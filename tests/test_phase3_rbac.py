"""
Tests for Phase 3 RBAC (Role-Based Access Control).

Tests role management, permissions, and role assignment.
"""

import pytest
from sqlalchemy.orm import Session

from backend.app.core.security import generate_id
from backend.app.repositories.role import RoleRepository
from backend.app.repositories.permission import PermissionRepository
from backend.app.repositories.user_role import UserRoleRepository
from backend.app.services.role import RoleService
from backend.app.services.permission import PermissionService
from backend.app.models.role import Role
from backend.app.models.permission import Permission
from backend.app.models.user_role import UserRole
from backend.app.core.exceptions import NotFoundError, ValidationError
from backend.app.core.permissions import DEFAULT_PERMISSIONS, PermissionCode


@pytest.fixture
def tenant_id() -> str:
    return generate_request_id()


@pytest.fixture
def user_id() -> str:
    return generate_request_id()


@pytest.fixture
def permission_service(db_session: Session) -> PermissionService:
    return PermissionService(db_session)


@pytest.fixture
def role_service(db_session: Session) -> RoleService:
    return RoleService(db_session)


@pytest.fixture
def seed_permissions(permission_service: PermissionService):
    """Seed default permissions before tests."""
    permission_service.seed_permissions()


class TestPermissionRepository:
    """Tests for PermissionRepository."""

    def test_create_permission(self, db_session: Session):
        """Test creating a permission."""
        repo = PermissionRepository(db_session)
        permission = repo.create(PermissionCode.USER_CREATE, "Create users")

        assert permission.code == PermissionCode.USER_CREATE
        assert permission.description == "Create users"

    def test_get_permission_by_id(self, db_session: Session):
        """Test getting permission by ID."""
        repo = PermissionRepository(db_session)
        permission = repo.create(PermissionCode.USER_READ, "Read users")

        retrieved = repo.get_by_id(permission.id)
        assert retrieved.id == permission.id
        assert retrieved.code == PermissionCode.USER_READ

    def test_get_permission_by_code(self, db_session: Session):
        """Test getting permission by code."""
        repo = PermissionRepository(db_session)
        permission = repo.create(PermissionCode.ROLE_CREATE, "Create roles")

        retrieved = repo.get_by_code(PermissionCode.ROLE_CREATE)
        assert retrieved.id == permission.id
        assert retrieved.code == PermissionCode.ROLE_CREATE

    def test_list_all_permissions(self, db_session: Session, seed_permissions):
        """Test listing all permissions."""
        repo = PermissionRepository(db_session)
        permissions = repo.list_all()

        assert len(permissions) == len(DEFAULT_PERMISSIONS)

    def test_get_permissions_by_codes(self, db_session: Session, seed_permissions):
        """Test getting permissions by list of codes."""
        repo = PermissionRepository(db_session)
        codes = [PermissionCode.USER_CREATE, PermissionCode.USER_READ]
        permissions = repo.get_by_codes(codes)

        assert len(permissions) == 2
        assert all(p.code in codes for p in permissions)


class TestRoleRepository:
    """Tests for RoleRepository."""

    def test_create_role(self, db_session: Session, tenant_id: str):
        """Test creating a role."""
        repo = RoleRepository(db_session)
        role = repo.create(tenant_id, "Admin", "Administrator role")

        assert role.name == "Admin"
        assert role.tenant_id == tenant_id
        assert role.status == "active"

    def test_get_role_by_id(self, db_session: Session, tenant_id: str):
        """Test getting role by ID."""
        repo = RoleRepository(db_session)
        role = repo.create(tenant_id, "Editor", "Editor role")

        retrieved = repo.get_by_id(role.id, tenant_id)
        assert retrieved.id == role.id
        assert retrieved.name == "Editor"

    def test_get_role_by_id_wrong_tenant(self, db_session: Session, tenant_id: str):
        """Test getting role with wrong tenant returns None."""
        repo = RoleRepository(db_session)
        role = repo.create(tenant_id, "Viewer", "Viewer role")

        wrong_tenant = generate_request_id()
        retrieved = repo.get_by_id(role.id, wrong_tenant)
        assert retrieved is None

    def test_get_role_by_name(self, db_session: Session, tenant_id: str):
        """Test getting role by name."""
        repo = RoleRepository(db_session)
        role = repo.create(tenant_id, "Manager", "Manager role")

        retrieved = repo.get_by_name(tenant_id, "Manager")
        assert retrieved.id == role.id

    def test_list_roles_by_tenant(self, db_session: Session, tenant_id: str):
        """Test listing roles by tenant."""
        repo = RoleRepository(db_session)
        repo.create(tenant_id, "Admin", "Admin")
        repo.create(tenant_id, "Editor", "Editor")

        roles = repo.list_by_tenant(tenant_id)
        assert len(roles) == 2

    def test_list_roles_other_tenant_isolated(self, db_session: Session):
        """Test that roles from different tenants are isolated."""
        repo = RoleRepository(db_session)
        tenant_1 = generate_request_id()
        tenant_2 = generate_request_id()

        repo.create(tenant_1, "Admin", "Admin")
        repo.create(tenant_2, "Viewer", "Viewer")

        roles_tenant_1 = repo.list_by_tenant(tenant_1)
        assert len(roles_tenant_1) == 1
        assert roles_tenant_1[0].name == "Admin"

    def test_update_role(self, db_session: Session, tenant_id: str):
        """Test updating a role."""
        repo = RoleRepository(db_session)
        role = repo.create(tenant_id, "OldName", "Old description")

        updated = repo.update(role.id, tenant_id, name="NewName", description="New description")
        assert updated.name == "NewName"
        assert updated.description == "New description"

    def test_delete_role(self, db_session: Session, tenant_id: str):
        """Test deleting a role."""
        repo = RoleRepository(db_session)
        role = repo.create(tenant_id, "ToDelete", "Delete this")

        repo.delete(role.id, tenant_id)
        retrieved = repo.get_by_id(role.id, tenant_id)
        assert retrieved is None


class TestRoleService:
    """Tests for RoleService."""

    def test_create_role_service(self, db_session: Session, tenant_id: str, role_service: RoleService):
        """Test creating a role via service."""
        role = role_service.create_role(tenant_id, "Admin", "Administrator")

        assert role.name == "Admin"
        assert role.tenant_id == tenant_id

    def test_create_role_duplicate_name(self, db_session: Session, tenant_id: str, role_service: RoleService):
        """Test that duplicate role names are rejected."""
        role_service.create_role(tenant_id, "Admin", "First admin")

        with pytest.raises(ValidationError):
            role_service.create_role(tenant_id, "Admin", "Second admin")

    def test_list_roles_service(self, db_session: Session, tenant_id: str, role_service: RoleService):
        """Test listing roles via service."""
        role_service.create_role(tenant_id, "Admin", "Admin role")
        role_service.create_role(tenant_id, "Editor", "Editor role")

        roles = role_service.list_roles(tenant_id)
        assert len(roles) == 2

    def test_get_role_service(self, db_session: Session, tenant_id: str, role_service: RoleService):
        """Test getting a role via service."""
        role = role_service.create_role(tenant_id, "Manager", "Manager role")

        retrieved = role_service.get_role(role.id, tenant_id)
        assert retrieved.id == role.id
        assert retrieved.name == "Manager"

    def test_get_role_not_found(self, db_session: Session, tenant_id: str, role_service: RoleService):
        """Test getting non-existent role raises NotFoundError."""
        fake_id = generate_request_id()
        with pytest.raises(NotFoundError):
            role_service.get_role(fake_id, tenant_id)

    def test_update_role_service(self, db_session: Session, tenant_id: str, role_service: RoleService):
        """Test updating a role via service."""
        role = role_service.create_role(tenant_id, "Admin", "Old description")

        updated = role_service.update_role(role.id, tenant_id, name="SuperAdmin", description="New desc")
        assert updated.name == "SuperAdmin"
        assert updated.description == "New desc"

    def test_delete_role_service(self, db_session: Session, tenant_id: str, role_service: RoleService):
        """Test deleting a role via service."""
        role = role_service.create_role(tenant_id, "Temporary", "To delete")

        role_service.delete_role(role.id, tenant_id)

        with pytest.raises(NotFoundError):
            role_service.get_role(role.id, tenant_id)

    def test_add_permission_to_role(self, db_session: Session, tenant_id: str, role_service: RoleService, seed_permissions):
        """Test adding permission to role."""
        role = role_service.create_role(tenant_id, "Admin", "Admin")

        # Get a permission from database
        perm_repo = PermissionRepository(db_session)
        perms = perm_repo.list_all()
        assert len(perms) > 0

        permission = perms[0]
        role = role_service.add_permission_to_role(role.id, permission.id, tenant_id)

        assert len(role.permissions) > 0
        assert permission.id in [p.id for p in role.permissions]

    def test_get_role_permissions(self, db_session: Session, tenant_id: str, role_service: RoleService, seed_permissions):
        """Test getting role permissions."""
        role = role_service.create_role(tenant_id, "Editor", "Editor")

        perm_repo = PermissionRepository(db_session)
        all_perms = perm_repo.list_all()

        role_service.add_permission_to_role(role.id, all_perms[0].id, tenant_id)
        role_service.add_permission_to_role(role.id, all_perms[1].id, tenant_id)

        permissions = role_service.get_role_permissions(role.id, tenant_id)
        assert len(permissions) == 2


class TestUserRoleRepository:
    """Tests for UserRoleRepository."""

    def test_assign_role_to_user(self, db_session: Session, tenant_id: str, user_id: str):
        """Test assigning a role to user."""
        # Create a role first
        role_repo = RoleRepository(db_session)
        role = role_repo.create(tenant_id, "Admin", "Admin")

        # Assign role
        user_role_repo = UserRoleRepository(db_session)
        user_role = user_role_repo.assign(user_id, role.id, tenant_id)

        assert user_role.user_id == user_id
        assert user_role.role_id == role.id
        assert user_role.tenant_id == tenant_id

    def test_assign_role_idempotent(self, db_session: Session, tenant_id: str, user_id: str):
        """Test that assigning same role twice is idempotent."""
        role_repo = RoleRepository(db_session)
        role = role_repo.create(tenant_id, "Manager", "Manager")

        user_role_repo = UserRoleRepository(db_session)
        user_role_1 = user_role_repo.assign(user_id, role.id, tenant_id)
        user_role_2 = user_role_repo.assign(user_id, role.id, tenant_id)

        assert user_role_1.id == user_role_2.id

    def test_unassign_role_from_user(self, db_session: Session, tenant_id: str, user_id: str):
        """Test removing a role from user."""
        role_repo = RoleRepository(db_session)
        role = role_repo.create(tenant_id, "Editor", "Editor")

        user_role_repo = UserRoleRepository(db_session)
        user_role_repo.assign(user_id, role.id, tenant_id)

        user_role_repo.unassign(user_id, role.id, tenant_id)

        retrieved = user_role_repo.get_user_roles(user_id, tenant_id)
        assert len(retrieved) == 0

    def test_get_user_roles(self, db_session: Session, tenant_id: str, user_id: str):
        """Test getting all roles for a user."""
        role_repo = RoleRepository(db_session)
        role_1 = role_repo.create(tenant_id, "Admin", "Admin")
        role_2 = role_repo.create(tenant_id, "Editor", "Editor")

        user_role_repo = UserRoleRepository(db_session)
        user_role_repo.assign(user_id, role_1.id, tenant_id)
        user_role_repo.assign(user_id, role_2.id, tenant_id)

        user_roles = user_role_repo.get_user_roles(user_id, tenant_id)
        assert len(user_roles) == 2

    def test_has_role(self, db_session: Session, tenant_id: str, user_id: str):
        """Test checking if user has a role."""
        role_repo = RoleRepository(db_session)
        role = role_repo.create(tenant_id, "Viewer", "Viewer")

        user_role_repo = UserRoleRepository(db_session)
        user_role_repo.assign(user_id, role.id, tenant_id)

        assert user_role_repo.has_role(user_id, role.id, tenant_id)

        # Check for non-existent role
        fake_role_id = generate_request_id()
        assert not user_role_repo.has_role(user_id, fake_role_id, tenant_id)

    def test_user_role_isolation_by_tenant(self, db_session: Session, user_id: str):
        """Test that user roles are isolated by tenant."""
        tenant_1 = generate_request_id()
        tenant_2 = generate_request_id()

        # Create roles in different tenants
        role_repo = RoleRepository(db_session)
        role_1 = role_repo.create(tenant_1, "Admin", "Admin")
        role_2 = role_repo.create(tenant_2, "Viewer", "Viewer")

        # Assign roles
        user_role_repo = UserRoleRepository(db_session)
        user_role_repo.assign(user_id, role_1.id, tenant_1)
        user_role_repo.assign(user_id, role_2.id, tenant_2)

        # Check isolation
        roles_tenant_1 = user_role_repo.get_user_roles(user_id, tenant_1)
        roles_tenant_2 = user_role_repo.get_user_roles(user_id, tenant_2)

        assert len(roles_tenant_1) == 1
        assert len(roles_tenant_2) == 1
        assert roles_tenant_1[0].role_id == role_1.id
        assert roles_tenant_2[0].role_id == role_2.id
