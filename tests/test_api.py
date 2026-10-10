"""API integration tests for the locally runnable Nexora backend."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi.testclient import TestClient

from app.models.invoice import Invoice, InvoiceStatus
from app.models.api_key import APIKey
from app.models.data_export import DataExport, DataExportStatus
from app.models.payment_method import PaymentMethod
from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.user_role import UserRole


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


def create_plan(client: TestClient, suffix: str, tier: str = "starter") -> dict:
    response = client.post(
        "/api/v1/plans",
        json={
            "name": f"Pytest {suffix}",
            "slug": f"pytest-{suffix}".lower(),
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
    assert me.json()["data"]["user"]["email"] == account["email"]

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

    assert client.post(f"/api/v1/applications/{application_id}/suspend").status_code == 200
    assert client.delete(f"/api/v1/applications/{application_id}").status_code == 204


def test_billing_plan_subscription_usage_and_invoice_endpoints(
    client: TestClient,
    db_session,
    registered_user,
):
    user = registered_user["user"]
    tenant = registered_user["tenant"]
    grant_permissions(
        db_session,
        user["id"],
        tenant["id"],
        ["admin:plan:create", "admin:plan:update"],
    )

    assert client.get("/api/v1/plans").status_code == 200
    first = create_plan(client, "starter", "starter")
    second = create_plan(client, "professional", "professional")
    assert client.get(f"/api/v1/plans/{first['id']}").status_code == 200
    updated_plan = client.put(
        f"/api/v1/plans/{first['id']}",
        json={"description": "Updated through the API"},
    )
    assert updated_plan.status_code == 200

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
    assert payment.status_code == 200, payment.text
    assert payment.json()["invoice"]["status"] == "paid"

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
    assert retry.status_code == 200, retry.text

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
    ).status_code == 404
    assert client.post(f"/api/v1/invoices/{missing}/retry").status_code == 404

    invalid_role = client.post("/api/v1/roles", json={"name": ""})
    assert invalid_role.status_code == 422
