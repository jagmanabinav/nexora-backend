"""Provision the first platform administrator from explicit environment values."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy.orm import Session

from app.core.constants import TENANT_STATUS_ACTIVE
from app.core.permissions import DEFAULT_PERMISSIONS, DEFAULT_ROLES
from app.core.security import hash_password
from app.database.connection import SessionLocal
import app.main  # noqa: F401  # Registers all SQLAlchemy models before queries.
from app.models.permission import Permission
from app.models.application import Application
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.tenant import Tenant
from app.models.user import User
from app.models.user_role import UserRole


def _required_setting(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"{name} must be set before running this bootstrap.")
    return value


def _validate_password(password: str) -> None:
    if len(password) < 12:
        raise SystemExit("BOOTSTRAP_ADMIN_PASSWORD must be at least 12 characters.")
    if not any(char.isupper() for char in password):
        raise SystemExit("BOOTSTRAP_ADMIN_PASSWORD must contain an uppercase letter.")
    if not any(char.islower() for char in password):
        raise SystemExit("BOOTSTRAP_ADMIN_PASSWORD must contain a lowercase letter.")
    if not any(char.isdigit() for char in password):
        raise SystemExit("BOOTSTRAP_ADMIN_PASSWORD must contain a digit.")


def provision(session: Session, email: str, password: str, first_name: str, last_name: str) -> None:
    sensitive_codes = {
        "admin:plan:create",
        "admin:tenant_application:review",
    }
    tenant = session.query(Tenant).filter(Tenant.slug == "nexora-platform").first()
    privileged_role_query = (
        session.query(Role)
        .join(RolePermission, RolePermission.role_id == Role.id)
        .join(Permission, Permission.id == RolePermission.permission_id)
        .filter(Permission.code.in_(sensitive_codes))
    )
    if tenant:
        privileged_role_query = privileged_role_query.filter(
            Role.tenant_id == tenant.id
        )
    else:
        privileged_role_query = privileged_role_query.filter(False)
    privileged_role = privileged_role_query.first()
    if privileged_role:
        raise SystemExit(
            "Platform administrator permissions are already assigned; "
            "refusing to create another bootstrap account."
        )

    if session.query(User).filter(User.email == email).first():
        raise SystemExit("The requested administrator email already belongs to an account.")

    if tenant and session.query(User).filter(User.tenant_id == tenant.id).first():
        raise SystemExit("The reserved platform tenant already has users; refusing to modify it.")
    if tenant is None:
        tenant = Tenant(
            name="Nexora Platform",
            slug="nexora-platform",
            status=TENANT_STATUS_ACTIVE,
            email=email,
            configuration={},
        )
        session.add(tenant)
        session.flush()

    platform_fabwash = (
        session.query(Application)
        .filter(
            Application.tenant_id == tenant.id,
            Application.name == "FabWash",
        )
        .first()
    )
    if platform_fabwash is None:
        session.add(
            Application(
                tenant_id=tenant.id,
                name="FabWash",
                description="Textile fabric washing and processing workspace.",
                status="active",
                configuration='{"product_code":"fabwash"}',
            )
        )

    user = User(
        tenant_id=tenant.id,
        email=email,
        password_hash=hash_password(password),
        first_name=first_name,
        last_name=last_name,
        status="ACTIVE",
        email_verified=True,
    )
    session.add(user)
    session.flush()

    permissions = {}
    for code in DEFAULT_ROLES["super_admin"]["permissions"]:
        permission = session.query(Permission).filter(Permission.code == code).first()
        if permission is None:
            permission = Permission(code=code, description=DEFAULT_PERMISSIONS[code])
            session.add(permission)
            session.flush()
        permissions[code] = permission

    role = Role(
        tenant_id=tenant.id,
        name=DEFAULT_ROLES["super_admin"]["name"],
        description=DEFAULT_ROLES["super_admin"]["description"],
        status="active",
    )
    session.add(role)
    session.flush()
    session.add_all(
        RolePermission(role_id=role.id, permission_id=permission.id)
        for permission in permissions.values()
    )
    session.add(UserRole(user_id=user.id, role_id=role.id, tenant_id=tenant.id))
    session.commit()


def main() -> None:
    email = _required_setting("BOOTSTRAP_ADMIN_EMAIL")
    password = _required_setting("BOOTSTRAP_ADMIN_PASSWORD")
    first_name = _required_setting("BOOTSTRAP_ADMIN_FIRST_NAME")
    last_name = _required_setting("BOOTSTRAP_ADMIN_LAST_NAME")
    _validate_password(password)

    session = SessionLocal()
    try:
        provision(session, email, password, first_name, last_name)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
    print(f"Platform Super Admin provisioned for {email}.")


if __name__ == "__main__":
    main()
