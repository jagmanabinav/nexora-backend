"""Tenant application registration and Super Admin approval."""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.authorization import require_permission
from app.core.constants import (
    TENANT_STATUS_ACTIVE,
    TENANT_STATUS_PENDING,
    TENANT_STATUS_REJECTED,
)
from app.core.dependencies import (
    RequestContext,
    get_current_user_with_roles,
    get_db_session,
    get_request_id,
)
from app.core.exceptions import ConflictException, ResourceNotFoundException
from app.models.subscription import BillingCycle, Subscription, SubscriptionStatus
from app.models.tenant_application import TenantApplication
from app.models.user import User
from app.repositories.plan import PlanRepository
from app.repositories.tenant import TenantRepository
from app.repositories.user import UserRepository
from app.core.security import hash_password
from app.schemas.onboarding import (
    TenantApplicationCreate,
    TenantApplicationDecision,
    TenantApplicationResponse,
)
from app.schemas.response import SuccessResponse
from app.services.authentication import AuthenticationService

router = APIRouter(tags=["tenant onboarding"])


def _require_platform_admin(current_user: RequestContext, session: Session) -> None:
    tenant = TenantRepository(session).get_by_id(current_user.tenant_id)
    if (
        not tenant
        or tenant.slug != "nexora-platform"
        or not current_user.has_role("Super Admin")
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only a platform Super Admin may review company registrations",
        )


def _application_response(application: TenantApplication, owner: User | None = None) -> dict:
    tenant = application.tenant
    return {
        "id": application.id,
        "tenant_id": tenant.id,
        "company_name": tenant.name,
        "company_slug": tenant.slug,
        "company_email": tenant.email,
        "company_phone": tenant.phone,
        "owner_email": owner.email if owner else "",
        "owner_first_name": owner.first_name if owner else None,
        "owner_last_name": owner.last_name if owner else None,
        "application_code": application.application_code,
        "plan_id": application.requested_plan_id,
        "plan_name": application.requested_plan.name,
        "plan_max_users": application.requested_plan.max_users,
        "monthly_price": application.requested_plan.monthly_price,
        "annual_price": application.requested_plan.annual_price,
        "billing_cycle": application.billing_cycle,
        "status": application.status,
        "submitted_at": application.created_at,
        "reviewed_at": application.reviewed_at,
        "rejection_reason": application.rejection_reason,
    }


@router.post(
    "/tenant-applications",
    response_model=SuccessResponse[TenantApplicationResponse],
    status_code=status.HTTP_201_CREATED,
)
def create_tenant_application(
    request: TenantApplicationCreate,
    session: Session = Depends(get_db_session),
    request_id: str = Depends(get_request_id),
):
    """Register a company for a product; access remains locked until approval."""
    try:
        plan = PlanRepository(session).get_by_id(str(request.plan_id))
    except ResourceNotFoundException as error:
        raise HTTPException(status_code=404, detail="Selected plan is not available") from error
    if not plan.is_active:
        raise HTTPException(status_code=404, detail="Selected plan is not available")
    if plan.application_code != request.application_code:
        raise HTTPException(
            status_code=422,
            detail="Selected plan is not available for this application",
        )
    if request.billing_cycle == "lifetime":
        if plan.monthly_price or plan.annual_price or plan.setup_fee <= 0:
            raise HTTPException(
                status_code=422,
                detail="Selected plan does not offer lifetime billing",
            )
    elif request.billing_cycle == "annual" and plan.annual_price <= 0:
        raise HTTPException(
            status_code=422,
            detail="Selected plan does not offer annual billing",
        )
    try:
        tenant_repo = TenantRepository(session)
        existing_tenant = tenant_repo.get_by_slug(request.company_slug)
        if existing_tenant:
            owner = UserRepository(session).get_by_email(request.owner_email)
            rejected_request = (
                session.query(TenantApplication)
                .filter(
                    TenantApplication.tenant_id == existing_tenant.id,
                    TenantApplication.status == "rejected",
                )
                .first()
            )
            if (
                existing_tenant.status != TENANT_STATUS_REJECTED
                or not rejected_request
                or not owner
                or owner.tenant_id != existing_tenant.id
            ):
                raise ConflictException(
                    f"Company slug '{request.company_slug}' is already registered"
                )

            existing_tenant.name = request.company_name
            existing_tenant.email = request.company_email
            existing_tenant.phone = request.company_phone
            existing_tenant.status = TENANT_STATUS_PENDING
            owner.password_hash = hash_password(request.owner_password)
            owner.first_name = request.owner_first_name
            owner.last_name = request.owner_last_name
            result = {"tenant": existing_tenant, "user": owner}
        else:
            result = AuthenticationService(session).register(
                email=request.owner_email,
                password=request.owner_password,
                first_name=request.owner_first_name,
                last_name=request.owner_last_name,
                tenant_name=request.company_name,
                tenant_slug=request.company_slug,
                tenant_status=TENANT_STATUS_PENDING,
                tenant_email=request.company_email,
                tenant_phone=request.company_phone,
                issue_tokens=False,
            )
    except ConflictException as error:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))

    application = TenantApplication(
        tenant_id=result["tenant"].id,
        requested_plan_id=plan.id,
        application_code=request.application_code,
        billing_cycle=request.billing_cycle,
        status="pending",
    )
    session.add(application)
    session.commit()
    session.refresh(application)
    application.tenant = result["tenant"]
    application.requested_plan = plan
    owner = result["user"]
    payload = _application_response(application)
    payload["owner_email"] = owner.email
    payload["owner_first_name"] = owner.first_name
    payload["owner_last_name"] = owner.last_name
    return SuccessResponse(
        data=payload,
        message="Registration submitted. Your account will be available after approval.",
        request_id=request_id,
    )


@router.get(
    "/tenant-applications",
    response_model=list[TenantApplicationResponse],
)
@require_permission("admin:tenant_application:review")
def list_tenant_applications(
    status_filter: str = "pending",
    current_user: RequestContext = Depends(get_current_user_with_roles),
    session: Session = Depends(get_db_session),
):
    _require_platform_admin(current_user, session)
    if status_filter not in {"pending", "approved", "rejected"}:
        raise HTTPException(status_code=400, detail="Invalid application status")

    applications = (
        session.query(TenantApplication)
        .filter(TenantApplication.status == status_filter)
        .order_by(TenantApplication.created_at.asc())
        .all()
    )
    result = []
    for application in applications:
        owner = (
            session.query(User)
            .filter(User.tenant_id == application.tenant_id)
            .order_by(User.created_at.asc())
            .first()
        )
        result.append(TenantApplicationResponse.model_validate(_application_response(application, owner)))
    return result


@router.post(
    "/tenant-applications/{application_id}/approve",
    response_model=TenantApplicationResponse,
)
@require_permission("admin:tenant_application:review")
def approve_tenant_application(
    application_id: str,
    current_user: RequestContext = Depends(get_current_user_with_roles),
    session: Session = Depends(get_db_session),
):
    _require_platform_admin(current_user, session)
    application = (
        session.query(TenantApplication)
        .filter(TenantApplication.id == application_id)
        .with_for_update()
        .first()
    )
    if not application:
        raise HTTPException(status_code=404, detail="Tenant application not found")
    if application.status != "pending":
        raise HTTPException(status_code=409, detail="Application has already been reviewed")

    tenant = TenantRepository(session).get_by_id(application.tenant_id)
    if not tenant or tenant.status != TENANT_STATUS_PENDING:
        raise HTTPException(status_code=409, detail="Tenant is not awaiting approval")
    try:
        plan = PlanRepository(session).get_by_id(str(application.requested_plan_id))
    except ResourceNotFoundException as error:
        raise HTTPException(status_code=409, detail="The requested plan is no longer available") from error
    if plan.application_code != application.application_code:
        raise HTTPException(
            status_code=409,
            detail="The requested plan no longer belongs to this application",
        )

    now = datetime.utcnow()
    cycle = BillingCycle(application.billing_cycle)
    if cycle == BillingCycle.MONTHLY:
        period_end = now + timedelta(days=30)
    elif cycle == BillingCycle.ANNUAL:
        period_end = now + timedelta(days=365)
    else:
        period_end = datetime(9999, 12, 31)
    subscription = Subscription(
        tenant_id=tenant.id,
        plan_id=plan.id,
        status=SubscriptionStatus.ACTIVE,
        billing_cycle=cycle,
        current_period_start=now,
        current_period_end=period_end,
        monthly_price=plan.monthly_price if cycle == BillingCycle.MONTHLY else 0,
        annual_price=plan.annual_price if cycle == BillingCycle.ANNUAL else 0,
        auto_renew=cycle != BillingCycle.LIFETIME,
        current_user_count=UserRepository(session).count_by_tenant(tenant.id),
    )
    session.add(subscription)
    tenant.status = TENANT_STATUS_ACTIVE
    application.status = "approved"
    application.reviewed_by = current_user.user_id
    application.reviewed_at = now
    session.commit()
    session.refresh(application)
    application.tenant = tenant
    application.requested_plan = plan
    owner = (
        session.query(User)
        .filter(User.tenant_id == application.tenant_id)
        .order_by(User.created_at.asc())
        .first()
    )
    return TenantApplicationResponse.model_validate(_application_response(application, owner))


@router.post(
    "/tenant-applications/{application_id}/reject",
    response_model=TenantApplicationResponse,
)
@require_permission("admin:tenant_application:review")
def reject_tenant_application(
    application_id: str,
    decision: TenantApplicationDecision,
    current_user: RequestContext = Depends(get_current_user_with_roles),
    session: Session = Depends(get_db_session),
):
    _require_platform_admin(current_user, session)
    application = (
        session.query(TenantApplication)
        .filter(TenantApplication.id == application_id)
        .with_for_update()
        .first()
    )
    if not application:
        raise HTTPException(status_code=404, detail="Tenant application not found")
    if application.status != "pending":
        raise HTTPException(status_code=409, detail="Application has already been reviewed")
    tenant = TenantRepository(session).get_by_id(application.tenant_id)
    if not tenant or tenant.status != TENANT_STATUS_PENDING:
        raise HTTPException(status_code=409, detail="Tenant is not awaiting approval")

    tenant.status = TENANT_STATUS_REJECTED
    application.status = "rejected"
    application.reviewed_by = current_user.user_id
    application.reviewed_at = datetime.utcnow()
    application.rejection_reason = decision.rejection_reason
    session.commit()
    session.refresh(application)
    application.tenant = tenant
    application.requested_plan = PlanRepository(session).get_by_id(
        str(application.requested_plan_id)
    )
    payload = _application_response(application)
    owner = (
        session.query(User)
        .filter(User.tenant_id == application.tenant_id)
        .order_by(User.created_at.asc())
        .first()
    )
    return TenantApplicationResponse.model_validate(_application_response(application, owner))
