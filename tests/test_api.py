"""API integration tests for the locally runnable Nexora backend."""

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.models.invoice import Invoice, InvoiceStatus
from app.models.api_key import APIKey
from app.models.application import Application
from app.models.data_export import DataExport, DataExportStatus
from app.models.payment_method import PaymentMethod
from app.models.plan import Plan, PlanTier
from app.models.subscription import BillingCycle, Subscription, SubscriptionStatus
from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.user_role import UserRole
from app.services.authentication import AuthenticationService


def grant_permissions(db_session, user_id: str, tenant_id: str, codes: list[str]) -> None:
    role = Role(tenant_id=UUID(tenant_id), name="pytest-admin", description="Test role")
    db_session.add(role)
    db_session.flush()

    for code in codes:
        permission = db_session.query(Permission).filter_by(code=code).first()
        if permission is None:
            permission = Permission(code=code, description="Permission used by API tests")
            db_session.add(permission)
            db_session.flush()
        db_session.add(RolePermission(role_id=role.id, permission_id=permission.id))

    db_session.add(
        UserRole(
            user_id=UUID(user_id),
            role_id=role.id,
            tenant_id=UUID(tenant_id),
        )
    )
    db_session.flush()


def create_plan(
    client: TestClient,
    suffix: str,
    tier: str = "starter",
    application_code: str = "fabwash",
) -> dict:
    response = client.post(
        "/api/v1/plans",
        json={
            "name": f"Pytest {suffix}",
            "slug": f"pytest-{suffix}".lower(),
            "application_code": application_code,
            "tier": tier,
            "monthly_price": 20,
            "annual_price": 200,
            "is_active": True,
            "is_default": False,
            "display_order": 0,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_health_readiness_and_api_root(client: TestClient):
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "healthy"

    ready = client.get("/ready")
    assert ready.status_code == 200
    assert ready.json()["status"] == "ready"

    root = client.get("/api/v1/")
    assert root.status_code == 200
    assert root.json()["status"] == "running"
    assert "X-Request-Id" in root.headers


def test_legacy_instant_tenant_registration_is_disabled(client: TestClient):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "legacy@example.com",
            "password": "LegacyPassword123",
            "first_name": "Legacy",
            "last_name": "User",
            "tenant_name": "Legacy Company",
            "tenant_slug": "legacy-company",
        },
    )
    assert response.status_code == 410
    assert "company application" in response.json()["detail"]


def test_plan_names_and_slugs_are_unique_per_application(db_session):
    db_session.add_all(
        [
            Plan(
                name="Starter",
                slug="starter",
                application_code="fabwash",
                tier=PlanTier.STARTER,
                monthly_price=10,
                annual_price=100,
            ),
            Plan(
                name="Starter",
                slug="starter",
                application_code="nexora",
                tier=PlanTier.STARTER,
                monthly_price=20,
                annual_price=200,
            ),
        ]
    )
    db_session.flush()


def test_platform_applications_include_fabwash(client, db_session, platform_admin):
    platform_tenant = (
        db_session.query(Application.tenant_id)
        .filter(Application.name == "FabWash")
        .first()
    )
    assert platform_tenant is not None

    response = client.get("/api/v1/applications")
    assert response.status_code == 200, response.text
    fabwash = [item for item in response.json() if item["name"] == "FabWash"]
    assert len(fabwash) == 1
    assert fabwash[0]["status"] == "active"


def test_fabwash_gst_invoice_issues_tenant_scoped_tax_totals(
    client, db_session, registered_user
):
    invoice_data = {
        "invoice_date": "2026-10-08",
        "due_date": "2026-10-23",
        "seller": {
            "name": "FabWash Demo Services",
            "address": "18 Industrial Road, Bengaluru, Karnataka 560058",
            "gstin": "29AABCF1234G1Z5",
            "state": "Karnataka",
            "state_code": "29",
        },
        "buyer": {
            "name": "Sample Fabric Buyer",
            "address": "42 Cotton Market Road, Bengaluru, Karnataka 560002",
            "gstin": "29AABCS5678H1Z2",
            "state": "Karnataka",
            "state_code": "29",
        },
        "place_of_supply": "Karnataka",
        "place_of_supply_code": "29",
        "line_items": [
            {
                "description": "Fabric washing and finishing",
                "sac": "998821",
                "quantity": "1200",
                "unit": "kg",
                "rate": "10",
                "gst_rate": "18",
            }
        ],
    }
    issued = client.post("/api/v1/fabwash/invoices", json=invoice_data)
    assert issued.status_code == 201, issued.text
    invoice = issued.json()
    assert invoice["invoice_number"] == "FW/2026-27/00001"
    assert invoice["supply_type"] == "intra-state"
    assert float(invoice["taxable_value"]) == 12000
    assert float(invoice["cgst_amount"]) == 1080
    assert float(invoice["sgst_amount"]) == 1080
    assert float(invoice["igst_amount"]) == 0
    assert float(invoice["invoice_total"]) == 14160

    invoices = client.get("/api/v1/fabwash/invoices")
    assert invoices.status_code == 200
    assert [row["id"] for row in invoices.json()] == [invoice["id"]]

    client.headers["Authorization"] = "Bearer invalid"
    unauthenticated = client.get(f"/api/v1/fabwash/invoices/{invoice['id']}")
    assert unauthenticated.status_code == 401

    client.headers["Authorization"] = (
        f"Bearer {registered_user['tokens']['access_token']}"
    )
    invalid_state = client.post(
        "/api/v1/fabwash/invoices",
        json={
            **invoice_data,
            "buyer": {**invoice_data["buyer"], "state_code": "08"},
        },
    )
    assert invalid_state.status_code == 422

    inter_state_data = {
        **invoice_data,
        "buyer": {
            **invoice_data["buyer"],
            "name": "Maharashtra Fabric Buyer",
            "address": "42 Cotton Market Road, Mumbai, Maharashtra 400001",
            "gstin": "27AABCS5678H1Z2",
            "state": "Maharashtra",
            "state_code": "27",
        },
        "place_of_supply": "Maharashtra",
        "place_of_supply_code": "27",
        "line_items": [
            {
                "description": "Fabric dyeing service",
                "sac": "998821",
                "quantity": "100",
                "unit": "kg",
                "rate": "250",
                "gst_rate": "18",
            }
        ],
    }
    inter_state = client.post("/api/v1/fabwash/invoices", json=inter_state_data)
    assert inter_state.status_code == 201, inter_state.text
    inter_invoice = inter_state.json()
    assert inter_invoice["invoice_number"] == "FW/2026-27/00002"
    assert inter_invoice["supply_type"] == "inter-state"
    assert float(inter_invoice["cgst_amount"]) == 0
    assert float(inter_invoice["sgst_amount"]) == 0
    assert float(inter_invoice["igst_amount"]) == 4500
    assert float(inter_invoice["invoice_total"]) == 29500

    other_suffix = uuid4().hex
    other = AuthenticationService(db_session).register(
        email=f"invoice-reader-{other_suffix}@example.com",
        password="LocalTest!2345",
        first_name="Other",
        last_name="Tenant",
        tenant_name="Other Invoice Tenant",
        tenant_slug=f"other-invoice-{other_suffix}",
    )
    db_session.commit()
    client.headers["Authorization"] = (
        f"Bearer {other['tokens']['access_token']}"
    )
    assert client.get("/api/v1/fabwash/invoices").json() == []
    assert (
        client.get(f"/api/v1/fabwash/invoices/{invoice['id']}").status_code
        == 404
    )


def test_expired_subscription_blocks_product_api_but_keeps_renewal_access(
    client, db_session, registered_user
):
    tenant_id = UUID(registered_user["tenant"]["id"])
    plan = Plan(
        name="Expired trial",
        slug="expired-trial",
        application_code="fabwash",
        tier=PlanTier.FREE,
        monthly_price=0,
        annual_price=0,
    )
    db_session.add(plan)
    db_session.flush()
    now = datetime.now(timezone.utc)
    subscription = Subscription(
        tenant_id=tenant_id,
        plan_id=plan.id,
        status=SubscriptionStatus.TRIAL,
        billing_cycle=BillingCycle.MONTHLY,
        current_period_start=now - timedelta(days=29),
        current_period_end=now + timedelta(days=1),
        monthly_price=0,
        annual_price=0,
    )
    db_session.add(subscription)
    db_session.commit()

    valid = client.get("/api/v1/fabwash/invoices")
    assert valid.status_code == 200
    subscription.current_period_end = now - timedelta(seconds=1)
    db_session.commit()

    blocked = client.get("/api/v1/fabwash/invoices")
    assert blocked.status_code == 403
    assert "Subscription expired" in blocked.json()["detail"]

    login = client.post(
        "/api/v1/auth/login",
        json={
            "email": registered_user["account"]["email"],
            "password": registered_user["account"]["password"],
        },
    )
    assert login.status_code == 403
    assert "Subscription expired" in login.json()["detail"]

    refresh = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": registered_user["tokens"]["refresh_token"]},
    )
    assert refresh.status_code == 403
    assert "Subscription expired" in refresh.json()["detail"]

    renewal = client.get("/api/v1/plans?application_code=fabwash")
    assert renewal.status_code == 200, renewal.text


def test_authentication_registration_login_refresh_and_logout(
    client: TestClient,
    registered_user,
):
    account = registered_user["account"]
    tokens = registered_user["tokens"]

    login = client.post(
        "/api/v1/auth/login",
        json={"email": account["email"], "password": account["password"]},
    )
    assert login.status_code == 200, login.text
    login_tokens = login.json()["data"]["tokens"]

    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    me_data = me.json()["data"]
    assert me_data["user"]["email"] == account["email"]
    assert [role["name"] for role in me_data["roles"]] == ["Admin"]
    assert "application:list" in me_data["permissions"]
    assert "application:create" in me_data["permissions"]

    refreshed = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": login_tokens["refresh_token"]},
    )
    assert refreshed.status_code == 200, refreshed.text
    refreshed_tokens = refreshed.json()["data"]["tokens"]
    assert refreshed_tokens["refresh_token"] != login_tokens["refresh_token"]

    client.headers["Authorization"] = f"Bearer {refreshed_tokens['access_token']}"
    logout = client.post("/api/v1/auth/logout")
    assert logout.status_code == 200, logout.text

    invalid_login = client.post(
        "/api/v1/auth/login",
        json={"email": account["email"], "password": "wrong-password"},
    )
    assert invalid_login.status_code == 401

    missing_refresh = client.post("/api/v1/auth/refresh", json={})
    assert missing_refresh.status_code == 400

    reused_refresh = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": login_tokens["refresh_token"]},
    )
    assert reused_refresh.status_code == 401

    assert tokens["access_token"]


def test_company_registration_approval_subscription_and_plan_user_limit(
    client: TestClient,
    db_session,
    platform_admin,
):
    suffix = platform_admin["account"]["email"].split("@")[0]
    plan = Plan(
        name=f"FabWash {suffix}",
        slug=f"fabwash-{suffix}",
        application_code="fabwash",
        tier=PlanTier.STARTER,
        monthly_price=30,
        annual_price=300,
        max_users=2,
        is_active=True,
        is_default=False,
    )
    db_session.add(plan)
    db_session.flush()
    other_application_plan = Plan(
        name=f"Nexora {suffix}",
        slug=f"nexora-{suffix}",
        application_code="nexora",
        tier=PlanTier.STARTER,
        monthly_price=20,
        annual_price=200,
        is_active=True,
        is_default=False,
    )
    db_session.add(other_application_plan)
    db_session.flush()
    application = {
        "application_code": "fabwash",
        "company_name": f"Fabric Co {suffix}",
        "company_slug": f"fabric-co-{suffix}",
        "owner_email": f"owner-{suffix}@example.com",
        "owner_password": "OwnerPassword123",
        "plan_id": str(plan.id),
        "billing_cycle": "monthly",
    }
    mismatched_application = {
        **application,
        "company_slug": f"wrong-plan-{suffix}",
        "owner_email": f"wrong-plan-{suffix}@example.com",
        "plan_id": str(other_application_plan.id),
    }
    mismatch_response = client.post(
        "/api/v1/tenant-applications", json=mismatched_application
    )
    assert mismatch_response.status_code == 422
    assert "not available for this application" in mismatch_response.json()["detail"]

    submitted = client.post("/api/v1/tenant-applications", json=application)
    assert submitted.status_code == 201, submitted.text
    request_data = submitted.json()["data"]
    assert request_data["status"] == "pending"
    assert request_data["plan_name"] == plan.name
    assert request_data["owner_email"] == application["owner_email"]
    assert request_data["owner_first_name"] is None
    assert request_data["owner_last_name"] is None
    assert request_data["company_email"] is None
    assert request_data["company_phone"] is None

    pending_login = client.post(
        "/api/v1/auth/login",
        json={
            "email": application["owner_email"],
            "password": application["owner_password"],
        },
    )
    assert pending_login.status_code == 403

    pending_requests = client.get("/api/v1/tenant-applications")
    assert pending_requests.status_code == 200
    assert [item["id"] for item in pending_requests.json()] == [request_data["id"]]

    approved = client.post(
        f"/api/v1/tenant-applications/{request_data['id']}/approve"
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved"

    owner_login = client.post(
        "/api/v1/auth/login",
        json={
            "email": application["owner_email"],
            "password": application["owner_password"],
        },
    )
    assert owner_login.status_code == 200, owner_login.text
    owner_tokens = owner_login.json()["data"]["tokens"]
    client.headers["Authorization"] = f"Bearer {owner_tokens['access_token']}"

    users = client.get("/api/v1/users")
    assert users.status_code == 200, users.text
    assert users.json()["plan_name"] == plan.name
    assert users.json()["max_users"] == 2
    assert users.json()["user_count"] == 1

    new_user = client.post(
        "/api/v1/users",
        json={
            "email": f"member-{suffix}@example.com",
            "password": "MemberPassword123",
            "first_name": "Plan",
            "last_name": "Member",
        },
    )
    assert new_user.status_code == 201, new_user.text
    assert new_user.json()["role_name"] == "Member"

    member_login = client.post(
        "/api/v1/auth/login",
        json={
            "email": f"member-{suffix}@example.com",
            "password": "MemberPassword123",
        },
    )
    assert member_login.status_code == 200, member_login.text
    client.headers["Authorization"] = (
        f"Bearer {member_login.json()['data']['tokens']['access_token']}"
    )
    forbidden_create = client.post(
        "/api/v1/users",
        json={
            "email": f"member-created-{suffix}@example.com",
            "password": "OtherPassword123",
            "first_name": "Not",
            "last_name": "Allowed",
        },
    )
    assert forbidden_create.status_code == 403

    client.headers["Authorization"] = f"Bearer {owner_tokens['access_token']}"
    over_limit = client.post(
        "/api/v1/users",
        json={
            "email": f"extra-{suffix}@example.com",
            "password": "ExtraPassword123",
            "first_name": "Over",
            "last_name": "Limit",
        },
    )
    assert over_limit.status_code == 403
    assert "allows up to 2 users" in over_limit.json()["detail"]


def test_lifetime_plan_approval_and_super_admin_plan_editing(
    client: TestClient,
    db_session,
    platform_admin,
):
    suffix = platform_admin["account"]["email"].split("@")[0]
    plan = Plan(
        name=f"Lifetime plan {suffix}",
        slug=f"lifetime-{suffix}",
        application_code="fabwash",
        tier=PlanTier.PROFESSIONAL,
        monthly_price=0,
        annual_price=0,
        setup_fee=9999,
        max_users=2,
        is_active=True,
        is_default=False,
    )
    db_session.add(plan)
    db_session.flush()

    updated = client.put(
        f"/api/v1/plans/{plan.id}",
        json={
            "slug": f"lifetime-updated-{suffix}",
            "tier": "enterprise",
            "setup_fee": 10999,
            "max_users": 3,
            "sso_enabled": True,
        },
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["slug"] == f"lifetime-updated-{suffix}"
    assert updated.json()["tier"] == "enterprise"
    assert updated.json()["setup_fee"] == 10999
    assert updated.json()["max_users"] == 3
    assert updated.json()["sso_enabled"] is True

    application = {
        "application_code": "fabwash",
        "company_name": f"Lifetime Fabric Co {suffix}",
        "company_slug": f"lifetime-fabric-{suffix}",
        "owner_email": f"lifetime-owner-{suffix}@example.com",
        "owner_password": "LifetimePassword123",
        "plan_id": str(plan.id),
        "billing_cycle": "lifetime",
    }
    submitted = client.post("/api/v1/tenant-applications", json=application)
    assert submitted.status_code == 201, submitted.text
    application_id = submitted.json()["data"]["id"]

    approved = client.post(
        f"/api/v1/tenant-applications/{application_id}/approve"
    )
    assert approved.status_code == 200, approved.text
    subscription = (
        db_session.query(Subscription)
        .filter_by(tenant_id=UUID(submitted.json()["data"]["tenant_id"]))
        .one()
    )
    assert subscription.billing_cycle == BillingCycle.LIFETIME
    assert subscription.current_period_end.year == 9999
    assert subscription.auto_renew is False


def test_rejected_tenant_application_cannot_login(client: TestClient, db_session, platform_admin):
    suffix = platform_admin["account"]["email"].split("@")[0]
    plan = Plan(
        name=f"Reject plan {suffix}",
        slug=f"reject-{suffix}",
        application_code="fabwash",
        tier=PlanTier.STARTER,
        monthly_price=10,
        annual_price=100,
        max_users=5,
        is_active=True,
        is_default=False,
    )
    db_session.add(plan)
    db_session.flush()
    application = {
        "company_name": f"Rejected Co {suffix}",
        "company_slug": f"rejected-co-{suffix}",
        "company_email": f"rejected-{suffix}@example.com",
        "owner_email": f"owner-rejected-{suffix}@example.com",
        "owner_password": "OwnerPassword123",
        "owner_first_name": "Reject",
        "owner_last_name": "Owner",
        "plan_id": str(plan.id),
        "billing_cycle": "annual",
    }
    submitted = client.post("/api/v1/tenant-applications", json=application)
    assert submitted.status_code == 201, submitted.text
    request_id = submitted.json()["data"]["id"]
    rejected = client.post(
        f"/api/v1/tenant-applications/{request_id}/reject",
        json={"rejection_reason": "Please provide additional company details."},
    )
    assert rejected.status_code == 200, rejected.text
    assert rejected.json()["status"] == "rejected"

    blocked_login = client.post(
        "/api/v1/auth/login",
        json={
            "email": f"owner-rejected-{suffix}@example.com",
            "password": "OwnerPassword123",
        },
    )
    assert blocked_login.status_code == 403

    resubmitted = client.post("/api/v1/tenant-applications", json=application)
    assert resubmitted.status_code == 201, resubmitted.text
    assert resubmitted.json()["data"]["status"] == "pending"
    assert resubmitted.json()["data"]["tenant_id"] == rejected.json()["tenant_id"]


def test_protected_routes_reject_missing_credentials(client: TestClient):
    for path in (
        "/api/v1/auth/me",
        "/api/v1/roles",
        "/api/v1/applications",
        "/api/v1/webhooks",
        "/api/v1/audit-logs",
    ):
        response = client.get(path)
        assert response.status_code == 401, (path, response.text)


def test_role_permission_crud(client: TestClient, db_session, registered_user):
    created = client.post(
        "/api/v1/roles",
        json={"name": "operator", "description": "Operations role"},
    )
    assert created.status_code == 201, created.text
    role = created.json()
    role_id = role["id"]

    listed = client.get("/api/v1/roles")
    assert listed.status_code == 200
    assert any(item["id"] == role_id for item in listed.json())

    fetched = client.get(f"/api/v1/roles/{role_id}")
    assert fetched.status_code == 200

    updated = client.put(
        f"/api/v1/roles/{role_id}",
        json={"name": "operator-updated", "description": "Updated role"},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "operator-updated"

    permissions = client.get("/api/v1/permissions")
    assert permissions.status_code == 200
    assert isinstance(permissions.json(), list)

    permission = Permission(code="pytest:read", description="Test permission")
    db_session.add(permission)
    db_session.flush()
    assigned = client.post(
        f"/api/v1/roles/{role_id}/permissions",
        json={"permission_ids": [str(permission.id)]},
    )
    assert assigned.status_code == 200, assigned.text
    assert assigned.json()["permissions"][0]["code"] == "pytest:read"

    platform_permission = Permission(
        code="admin:tenant_application:review",
        description="Platform-only company approval",
    )
    db_session.add(platform_permission)
    db_session.flush()
    blocked_platform_grant = client.post(
        f"/api/v1/roles/{role_id}/permissions",
        json={"permission_ids": [str(platform_permission.id)]},
    )
    assert blocked_platform_grant.status_code == 403
    assert (
        client.post(
            "/api/v1/plans",
            json={
                "name": "Tenant must not create platform plan",
                "slug": f"blocked-{registered_user['tenant']['slug']}",
                "tier": "starter",
                "monthly_price": 1,
                "annual_price": 10,
            },
        ).status_code
        == 403
    )

    user_id = registered_user["user"]["id"]
    assignment = client.post(
        f"/api/v1/users/{user_id}/roles",
        json={"role_id": role_id},
    )
    assert assignment.status_code == 201, assignment.text
    user_permissions = client.get(f"/api/v1/users/{user_id}/permissions")
    assert user_permissions.status_code == 200
    assert any(item["code"] == "pytest:read" for item in user_permissions.json())

    revoked = client.delete(f"/api/v1/users/{user_id}/roles/{role_id}")
    assert revoked.status_code == 204

    removed = client.delete(
        f"/api/v1/roles/{role_id}/permissions/{permission.id}",
    )
    assert removed.status_code == 204
    deleted = client.delete(f"/api/v1/roles/{role_id}")
    assert deleted.status_code == 204
    assert client.get(f"/api/v1/roles/{role_id}").status_code == 404


def test_application_api_key_and_oauth_crud(client: TestClient, db_session, registered_user):
    suffix = registered_user["tenant"]["slug"]
    created = client.post(
        "/api/v1/applications",
        json={
            "name": f"App {suffix}",
            "description": "API integration test",
            "webhook_url": "https://example.com/events",
        },
    )
    assert created.status_code == 201, created.text
    application_id = created.json()["id"]

    assert client.get("/api/v1/applications").status_code == 200
    assert client.get(f"/api/v1/applications/{application_id}").status_code == 200
    updated = client.put(
        f"/api/v1/applications/{application_id}",
        json={"name": f"Updated {suffix}"},
    )
    assert updated.status_code == 200
    assert client.post(f"/api/v1/applications/{application_id}/activate").status_code == 200

    assert client.get(f"/api/v1/applications/{application_id}/api-keys").status_code == 200
    key = client.post(
        f"/api/v1/applications/{application_id}/api-keys",
        json={"name": "pytest-key"},
    )
    assert key.status_code == 201, key.text
    assert key.json()["key"]
    key_record = db_session.query(APIKey).filter_by(id=UUID(key.json()["id"])).first()
    assert key_record is not None, key.json()
    revoke = client.delete(f"/api/v1/api-keys/{key.json()['id']}")
    assert revoke.status_code == 204, f"{revoke.text}; key={key.json()['id']}; stored={key_record.id}"

    providers = client.get(
        f"/api/v1/applications/{application_id}/oauth-providers",
    )
    assert providers.status_code == 200
    oauth = client.post(
        f"/api/v1/applications/{application_id}/oauth-providers",
        json={
            "provider_name": "google",
            "client_id": "pytest-client",
            "client_secret": "pytest-secret",
            "redirect_url": "https://example.com/oauth/callback",
            "scopes": "openid profile",
        },
    )
    assert oauth.status_code == 201, oauth.text

    suspended = client.post(f"/api/v1/applications/{application_id}/suspend")
    assert suspended.status_code == 200
    assert suspended.json()["status"] == "suspended"
    assert client.delete(f"/api/v1/applications/{application_id}").status_code == 405
    reactivated = client.post(f"/api/v1/applications/{application_id}/activate")
    assert reactivated.status_code == 200
    assert reactivated.json()["status"] == "active"


def test_billing_plan_subscription_usage_and_invoice_endpoints(
    client: TestClient,
    db_session,
    registered_user,
    platform_admin,
):
    user = registered_user["user"]
    tenant = registered_user["tenant"]

    assert client.get("/api/v1/plans").status_code == 200
    client.headers["Authorization"] = (
        f"Bearer {platform_admin['tokens']['access_token']}"
    )
    first = create_plan(client, "starter", "starter")
    second = create_plan(
        client, "professional", "professional", application_code="nexora"
    )
    fabwash_plans = client.get(
        "/api/v1/plans", params={"application_code": "fabwash"}
    ).json()
    assert [plan["id"] for plan in fabwash_plans] == [first["id"]]
    nexora_plans = client.get(
        "/api/v1/plans", params={"application_code": "nexora"}
    ).json()
    assert [plan["id"] for plan in nexora_plans] == [second["id"]]
    assert client.get(f"/api/v1/plans/{first['id']}").status_code == 200
    updated_plan = client.put(
        f"/api/v1/plans/{first['id']}",
        json={"description": "Updated through the API"},
    )
    assert updated_plan.status_code == 200
    client.headers["Authorization"] = (
        f"Bearer {registered_user['tokens']['access_token']}"
    )

    subscription_response = client.post(
        "/api/v1/subscriptions",
        json={
            "plan_id": first["id"],
            "billing_cycle": "monthly",
            "trial_days": 0,
            "auto_renew": True,
        },
    )
    assert subscription_response.status_code == 201, subscription_response.text
    subscription = subscription_response.json()
    assert client.get("/api/v1/subscriptions").status_code == 200
    assert client.put(
        "/api/v1/subscriptions",
        json={"auto_renew": False},
    ).status_code == 200

    assert client.get("/api/v1/usage").status_code == 200
    assert client.get("/api/v1/usage/limits").status_code == 200
    usage = client.post(
        "/api/v1/usage/track",
        json={"metric_name": "api_calls", "amount": 2, "description": "pytest"},
    )
    assert usage.status_code == 201, usage.text
    assert usage.json()["subscription_id"] == subscription["id"]
    assert client.get("/api/v1/billing/overview").status_code == 200

    upgrade = client.post(
        "/api/v1/subscriptions/upgrade",
        json={"new_plan_id": second["id"]},
    )
    assert upgrade.status_code == 200, upgrade.text
    assert upgrade.json()["subscription"]["plan_id"] == second["id"]

    downgrade = client.post(
        "/api/v1/subscriptions/downgrade",
        json={"new_plan_id": first["id"]},
    )
    assert downgrade.status_code == 200, downgrade.text

    invoice = Invoice(
        tenant_id=UUID(tenant["id"]),
        subscription_id=UUID(subscription["id"]),
        invoice_number=f"PYTEST-{tenant['slug']}",
        status=InvoiceStatus.FAILED,
        issue_date=datetime.now(timezone.utc).replace(tzinfo=None),
        due_date=(datetime.now(timezone.utc) + timedelta(days=7)).replace(tzinfo=None),
        subtotal=12,
        total_amount=12,
        paid_amount=0,
    )
    db_session.add(invoice)
    db_session.flush()

    assert client.get("/api/v1/invoices").status_code == 200
    assert client.get(f"/api/v1/invoices/{invoice.id}").status_code == 200
    payment = client.post(
        f"/api/v1/invoices/{invoice.id}/payment",
        json={"amount": 12, "payment_method": "pytest"},
    )
    assert payment.status_code == 503
    assert "provider is configured" in payment.json()["detail"]
    assert (
        client.get(f"/api/v1/invoices/{invoice.id}").json()["status"]
        == "failed"
    )

    retry_invoice = Invoice(
        tenant_id=UUID(tenant["id"]),
        subscription_id=UUID(subscription["id"]),
        invoice_number=f"PYTEST-RETRY-{tenant['slug']}",
        status=InvoiceStatus.FAILED,
        issue_date=datetime.now(timezone.utc).replace(tzinfo=None),
        due_date=(datetime.now(timezone.utc) + timedelta(days=7)).replace(tzinfo=None),
        subtotal=4,
        total_amount=4,
        paid_amount=0,
    )
    db_session.add(retry_invoice)
    db_session.flush()
    retry = client.post(f"/api/v1/invoices/{retry_invoice.id}/retry")
    assert retry.status_code == 503
    assert (
        client.get(f"/api/v1/invoices/{retry_invoice.id}").json()["status"]
        == "failed"
    )

    payment_method = PaymentMethod(
        tenant_id=UUID(tenant["id"]),
        stripe_payment_method_id=f"pm_{tenant['slug']}",
        stripe_customer_id=f"cus_{tenant['slug']}",
        payment_type="card",
        card_brand="visa",
        card_last_4="4242",
        card_exp_month="12",
        card_exp_year="2030",
        is_default=False,
        is_valid=True,
        is_active=True,
    )
    db_session.add(payment_method)
    db_session.flush()
    assert client.get("/api/v1/payment-methods").status_code == 200
    assert client.post(
        f"/api/v1/payment-methods/{payment_method.id}/default",
    ).status_code == 200
    assert client.delete(
        f"/api/v1/payment-methods/{payment_method.id}",
    ).status_code == 204

    cancellation = client.post(
        "/api/v1/subscriptions/cancel",
        json={"reason": "Test complete", "effective_immediately": True},
    )
    assert cancellation.status_code == 200


def test_billing_without_subscription_returns_valid_empty_usage(client: TestClient, registered_user):
    forbidden_plan = client.post(
        "/api/v1/plans",
        json={
            "name": "Forbidden plan",
            "slug": "forbidden-plan",
            "tier": "starter",
            "monthly_price": 1,
            "annual_price": 10,
        },
    )
    assert forbidden_plan.status_code == 403

    usage = client.get("/api/v1/usage")
    assert usage.status_code == 200
    assert usage.json()["status"] == "no_subscription"
    assert usage.json()["metrics"] == {}

    limits = client.get("/api/v1/usage/limits")
    assert limits.status_code == 200
    assert limits.json()["status"] == "no_subscription"

    overview = client.get("/api/v1/billing/overview")
    assert overview.status_code == 200
    assert overview.json()["status"] == "no_subscription"

    assert client.get("/api/v1/subscriptions").status_code == 404


def test_webhook_audit_and_data_export_endpoints(
    client: TestClient,
    db_session,
    registered_user,
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv("DATA_EXPORT_STORAGE_PATH", str(tmp_path / "exports"))
    webhook = client.post(
        "/api/v1/webhooks",
        json={
            "name": "pytest webhook",
            "url": "https://example.com/webhook",
            "events": ["user.created"],
            "description": "Test webhook",
        },
    )
    assert webhook.status_code == 201, webhook.text
    webhook_id = webhook.json()["id"]

    assert client.get("/api/v1/webhooks").status_code == 200
    assert client.get(f"/api/v1/webhooks/{webhook_id}").status_code == 200
    updated = client.put(
        f"/api/v1/webhooks/{webhook_id}",
        json={"name": "updated webhook", "is_active": True},
    )
    assert updated.status_code == 200, updated.text
    assert client.get(
        f"/api/v1/webhooks/{webhook_id}/deliveries",
    ).status_code == 200

    audit_logs = client.get("/api/v1/audit-logs")
    assert audit_logs.status_code == 200, audit_logs.text
    assert audit_logs.json()["total"] >= 1
    audit_id = audit_logs.json()["logs"][0]["id"]
    assert client.get(f"/api/v1/audit-logs/{audit_id}").status_code == 200

    exports = client.get("/api/v1/data-exports")
    assert exports.status_code == 200
    created = client.post(
        "/api/v1/data-exports",
        json={
            "format": "json",
            "include_users": True,
            "include_subscriptions": False,
            "include_invoices": False,
            "include_usage_data": False,
        },
    )
    assert created.status_code == 201, created.text
    export_id = created.json()["id"]
    assert client.get(f"/api/v1/data-exports/{export_id}").status_code == 200
    assert client.get(
        f"/api/v1/data-exports/{export_id}/download-url",
    ).status_code == 400
    assert client.delete(f"/api/v1/data-exports/{export_id}").status_code == 204

    completed_export = DataExport(
        tenant_id=UUID(registered_user["tenant"]["id"]),
        requested_by=UUID(registered_user["user"]["id"]),
        format="json",
        status=DataExportStatus.COMPLETED.value,
        file_size_bytes=128,
        file_name="pytest-export.json",
        download_token="pytest-download-token",
        download_token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        completed_at=datetime.now(timezone.utc),
    )
    db_session.add(completed_export)
    db_session.flush()
    download = client.get(
        f"/api/v1/data-exports/{completed_export.id}/download-url",
    )
    assert download.status_code == 200, download.text
    assert download.json()["file_size_bytes"] == 128

    deleted = client.delete(f"/api/v1/webhooks/{webhook_id}")
    assert deleted.status_code == 204


def test_missing_resources_and_validation_errors(client: TestClient, registered_user):
    missing = "00000000-0000-0000-0000-000000000000"
    assert client.get(f"/api/v1/roles/{missing}").status_code == 404
    assert client.get(f"/api/v1/applications/{missing}").status_code == 404
    assert client.get(f"/api/v1/invoices/{missing}").status_code == 404
    assert client.get(f"/api/v1/webhooks/{missing}").status_code == 404
    assert client.get(f"/api/v1/data-exports/{missing}").status_code == 404
    assert client.delete(f"/api/v1/payment-methods/{missing}").status_code == 404
    assert client.post(
        f"/api/v1/invoices/{missing}/payment",
        json={"amount": 1},
    ).status_code == 503
    assert client.post(f"/api/v1/invoices/{missing}/retry").status_code == 503

    invalid_role = client.post("/api/v1/roles", json={"name": ""})
    assert invalid_role.status_code == 422
