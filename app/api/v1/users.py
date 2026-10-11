"""Tenant-scoped user listing and plan-limited user provisioning."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.authorization import require_permission
from app.core.dependencies import (
    RequestContext,
    get_current_user_with_roles,
    get_db_session,
)
from app.core.permissions import DEFAULT_ROLES
from app.core.security import hash_password
from app.services.subscription_access import subscription_expired
from app.models.subscription import Subscription, SubscriptionStatus
from app.repositories.role import RoleRepository
from app.repositories.subscription import SubscriptionRepository
from app.repositories.user import UserRepository
from app.repositories.user_role import UserRoleRepository
from app.schemas.auth import UserResponse
from app.schemas.users import TenantUserCreate, TenantUsersResponse

router = APIRouter(tags=["tenant users"])


def _active_subscription(session: Session, tenant_id):
    subscription = SubscriptionRepository(session).get_any_active_subscription(tenant_id)
    if not subscription or subscription.status not in (
        SubscriptionStatus.ACTIVE,
        SubscriptionStatus.TRIAL,
    ) or subscription_expired(session, tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="An active subscription is required to manage tenant users",
        )
    return subscription


@router.get("/users", response_model=TenantUsersResponse)
@require_permission("user:list")
def list_tenant_users(
    current_user: RequestContext = Depends(get_current_user_with_roles),
    session: Session = Depends(get_db_session),
):
    subscription = _active_subscription(session, current_user.tenant_id)
    plan = subscription.plan
    users = UserRepository(session).list_by_tenant(current_user.tenant_id)
    assignments = UserRoleRepository(session)
    user_items = []
    for user in users:
        roles = assignments.get_user_roles(str(user.id), str(current_user.tenant_id))
        if roles:
            user_items.append(
                {
                    "user": UserResponse.model_validate(user),
                    "role_id": roles[0].role_id,
                    "role_name": roles[0].role.name,
                }
            )

    tenant_roles = RoleRepository(session).list_by_tenant(str(current_user.tenant_id))
    return TenantUsersResponse(
        users=user_items,
        roles=[
            {"id": str(role.id), "name": role.name, "description": role.description}
            for role in tenant_roles
        ],
        plan_name=plan.name,
        max_users=plan.max_users,
        user_count=len(users),
    )


@router.post("/users", status_code=status.HTTP_201_CREATED)
@require_permission("user:create")
def create_tenant_user(
    request: TenantUserCreate,
    current_user: RequestContext = Depends(get_current_user_with_roles),
    session: Session = Depends(get_db_session),
):
    active = _active_subscription(session, current_user.tenant_id)
    subscription = (
        session.query(Subscription)
        .filter(Subscription.id == active.id)
        .with_for_update()
        .one()
    )
    plan = subscription.plan
    user_repo = UserRepository(session)
    user_count = user_repo.count_by_tenant(current_user.tenant_id)
    if plan.max_users >= 0 and user_count >= plan.max_users:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"The {plan.name} plan allows up to {plan.max_users} users. Upgrade your plan to add more.",
        )
    if user_repo.get_by_email(request.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered",
        )

    role_repo = RoleRepository(session)
    role = (
        role_repo.get_by_id(str(request.role_id), str(current_user.tenant_id))
        if request.role_id
        else role_repo.get_by_name(
            str(current_user.tenant_id), DEFAULT_ROLES["member"]["name"]
        )
    )
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Requested role was not found in this tenant",
        )

    user = user_repo.create(
        tenant_id=current_user.tenant_id,
        email=request.email,
        password_hash=hash_password(request.password),
        first_name=request.first_name,
        last_name=request.last_name,
    )
    UserRoleRepository(session).assign(
        str(user.id), str(role.id), str(current_user.tenant_id)
    )
    subscription.current_user_count = user_count + 1
    session.commit()
    session.refresh(user)
    return {
        "user": UserResponse.model_validate(user),
        "role_id": role.id,
        "role_name": role.name,
    }
