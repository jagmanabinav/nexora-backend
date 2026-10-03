"""
Permissions constants and definitions for Nexora Core.

Defines all available permissions in the system. Each permission
represents a specific action or resource access capability.
"""


class PermissionCode:
    """Permission codes for RBAC."""

    # User Management
    USER_CREATE = "user:create"
    USER_READ = "user:read"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"
    USER_LIST = "user:list"

    # Role Management
    ROLE_CREATE = "role:create"
    ROLE_READ = "role:read"
    ROLE_UPDATE = "role:update"
    ROLE_DELETE = "role:delete"
    ROLE_LIST = "role:list"
    ROLE_ASSIGN = "role:assign"

    # Permission Management
    PERMISSION_READ = "permission:read"
    PERMISSION_LIST = "permission:list"

    # Tenant Management
    TENANT_READ = "tenant:read"
    TENANT_UPDATE = "tenant:update"
    TENANT_DELETE = "tenant:delete"
    TENANT_LIST = "tenant:list"

    # Application Management
    APPLICATION_CREATE = "application:create"
    APPLICATION_READ = "application:read"
    APPLICATION_UPDATE = "application:update"
    APPLICATION_DELETE = "application:delete"
    APPLICATION_LIST = "application:list"

    # Billing Management
    BILLING_READ = "billing:read"
    BILLING_UPDATE = "billing:update"

    # Audit Log Access
    AUDIT_LOG_READ = "audit_log:read"


# Define default permissions with descriptions
DEFAULT_PERMISSIONS = {
    PermissionCode.USER_CREATE: "Create new users in the tenant",
    PermissionCode.USER_READ: "View user details",
    PermissionCode.USER_UPDATE: "Update user information",
    PermissionCode.USER_DELETE: "Delete users",
    PermissionCode.USER_LIST: "List all users in the tenant",
    #
    PermissionCode.ROLE_CREATE: "Create new roles in the tenant",
    PermissionCode.ROLE_READ: "View role details",
    PermissionCode.ROLE_UPDATE: "Update role information",
    PermissionCode.ROLE_DELETE: "Delete roles",
    PermissionCode.ROLE_LIST: "List all roles in the tenant",
    PermissionCode.ROLE_ASSIGN: "Assign roles to users",
    #
    PermissionCode.PERMISSION_READ: "View permission details",
    PermissionCode.PERMISSION_LIST: "List all available permissions",
    #
    PermissionCode.TENANT_READ: "View tenant details",
    PermissionCode.TENANT_UPDATE: "Update tenant settings",
    PermissionCode.TENANT_DELETE: "Delete tenant",
    PermissionCode.TENANT_LIST: "List tenant (own tenant only)",
    #
    PermissionCode.APPLICATION_CREATE: "Create applications",
    PermissionCode.APPLICATION_READ: "View application details",
    PermissionCode.APPLICATION_UPDATE: "Update applications",
    PermissionCode.APPLICATION_DELETE: "Delete applications",
    PermissionCode.APPLICATION_LIST: "List applications",
    #
    PermissionCode.BILLING_READ: "View billing information",
    PermissionCode.BILLING_UPDATE: "Update billing settings",
    #
    PermissionCode.AUDIT_LOG_READ: "View audit logs",
}


# Define default roles with their permissions
DEFAULT_ROLES = {
    "super_admin": {
        "name": "Super Admin",
        "description": "Full platform access (can only be assigned by system admin)",
        "permissions": [
            PermissionCode.USER_CREATE,
            PermissionCode.USER_READ,
            PermissionCode.USER_UPDATE,
            PermissionCode.USER_DELETE,
            PermissionCode.USER_LIST,
            PermissionCode.ROLE_CREATE,
            PermissionCode.ROLE_READ,
            PermissionCode.ROLE_UPDATE,
            PermissionCode.ROLE_DELETE,
            PermissionCode.ROLE_LIST,
            PermissionCode.ROLE_ASSIGN,
            PermissionCode.PERMISSION_READ,
            PermissionCode.PERMISSION_LIST,
            PermissionCode.TENANT_READ,
            PermissionCode.TENANT_UPDATE,
            PermissionCode.TENANT_DELETE,
            PermissionCode.TENANT_LIST,
            PermissionCode.APPLICATION_CREATE,
            PermissionCode.APPLICATION_READ,
            PermissionCode.APPLICATION_UPDATE,
            PermissionCode.APPLICATION_DELETE,
            PermissionCode.APPLICATION_LIST,
            PermissionCode.BILLING_READ,
            PermissionCode.BILLING_UPDATE,
            PermissionCode.AUDIT_LOG_READ,
        ],
    },
    "admin": {
        "name": "Admin",
        "description": "Full tenant access",
        "permissions": [
            PermissionCode.USER_CREATE,
            PermissionCode.USER_READ,
            PermissionCode.USER_UPDATE,
            PermissionCode.USER_DELETE,
            PermissionCode.USER_LIST,
            PermissionCode.ROLE_CREATE,
            PermissionCode.ROLE_READ,
            PermissionCode.ROLE_UPDATE,
            PermissionCode.ROLE_DELETE,
            PermissionCode.ROLE_LIST,
            PermissionCode.ROLE_ASSIGN,
            PermissionCode.PERMISSION_READ,
            PermissionCode.PERMISSION_LIST,
            PermissionCode.TENANT_READ,
            PermissionCode.TENANT_UPDATE,
            PermissionCode.TENANT_LIST,
            PermissionCode.APPLICATION_CREATE,
            PermissionCode.APPLICATION_READ,
            PermissionCode.APPLICATION_UPDATE,
            PermissionCode.APPLICATION_DELETE,
            PermissionCode.APPLICATION_LIST,
            PermissionCode.BILLING_READ,
            PermissionCode.BILLING_UPDATE,
            PermissionCode.AUDIT_LOG_READ,
        ],
    },
    "manager": {
        "name": "Manager",
        "description": "User and application management",
        "permissions": [
            PermissionCode.USER_READ,
            PermissionCode.USER_UPDATE,
            PermissionCode.USER_LIST,
            PermissionCode.ROLE_READ,
            PermissionCode.ROLE_LIST,
            PermissionCode.PERMISSION_READ,
            PermissionCode.PERMISSION_LIST,
            PermissionCode.TENANT_READ,
            PermissionCode.APPLICATION_READ,
            PermissionCode.APPLICATION_UPDATE,
            PermissionCode.APPLICATION_LIST,
            PermissionCode.BILLING_READ,
        ],
    },
    "member": {
        "name": "Member",
        "description": "Standard member access",
        "permissions": [
            PermissionCode.USER_READ,
            PermissionCode.TENANT_READ,
            PermissionCode.APPLICATION_READ,
            PermissionCode.APPLICATION_LIST,
        ],
    },
}
