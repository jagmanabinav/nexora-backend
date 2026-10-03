from enum import Enum
from uuid import uuid4
from sqlalchemy.dialects.postgresql import UUID as UUID_TYPE
from sqlalchemy import String, DateTime, JSON, Text, Index, Integer, Column
from datetime import datetime, timezone

from app.models.base import Base, BaseTenantModel


class AuditAction(str, Enum):
    """Audit action types"""
    # Authentication
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    
    # User management
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
    USER_DELETED = "user_deleted"
    USER_INVITED = "user_invited"
    USER_ACCEPTED_INVITE = "user_accepted_invite"
    
    # Subscription management
    SUBSCRIPTION_CREATED = "subscription_created"
    SUBSCRIPTION_UPGRADED = "subscription_upgraded"
    SUBSCRIPTION_DOWNGRADED = "subscription_downgraded"
    SUBSCRIPTION_CANCELLED = "subscription_cancelled"
    SUBSCRIPTION_PAUSED = "subscription_paused"
    SUBSCRIPTION_RESUMED = "subscription_resumed"
    
    # Billing
    INVOICE_CREATED = "invoice_created"
    INVOICE_PAID = "invoice_paid"
    PAYMENT_METHOD_ADDED = "payment_method_added"
    PAYMENT_METHOD_DELETED = "payment_method_deleted"
    
    # Application management
    APPLICATION_CREATED = "application_created"
    APPLICATION_UPDATED = "application_updated"
    APPLICATION_DELETED = "application_deleted"
    
    # Webhook management
    WEBHOOK_CREATED = "webhook_created"
    WEBHOOK_UPDATED = "webhook_updated"
    WEBHOOK_DELETED = "webhook_deleted"
    
    # API Key management
    API_KEY_CREATED = "api_key_created"
    API_KEY_DELETED = "api_key_deleted"
    API_KEY_ROTATED = "api_key_rotated"
    
    # Data export
    DATA_EXPORT_REQUESTED = "data_export_requested"
    DATA_EXPORT_COMPLETED = "data_export_completed"
    
    # Role & permissions
    ROLE_CREATED = "role_created"
    ROLE_UPDATED = "role_updated"
    ROLE_DELETED = "role_deleted"
    ROLE_ASSIGNED = "role_assigned"
    ROLE_REVOKED = "role_revoked"
    
    # Tenant management
    TENANT_CREATED = "tenant_created"
    TENANT_UPDATED = "tenant_updated"
    TENANT_DELETED = "tenant_deleted"
    
    # Custom events
    CUSTOM = "custom"


class AuditLog(BaseTenantModel):
    """Complete audit trail of platform operations"""
    
    __tablename__ = "audit_logs"
    __allow_unmapped__ = True
    
    # Action info
    action = Column(String(100), nullable=False)
    resource_type = Column(String(100), nullable=False)  # user, subscription, invoice, etc.
    resource_id = Column(String(255), nullable=True)  # ID of the resource being modified
    
    # Actor info
    actor_user_id = Column(UUID_TYPE(as_uuid=True), nullable=True)  # User who performed the action
    actor_type = Column(String(50), default="user", nullable=False)  # user, system, api_key
    actor_ip = Column(String(45), nullable=True)  # IPv4 or IPv6 address
    actor_user_agent = Column(String(500), nullable=True)  # Browser/client info
    
    # Request info
    request_method = Column(String(10), nullable=True)  # GET, POST, PUT, DELETE, PATCH
    request_path = Column(String(500), nullable=True)  # API path
    request_id = Column(UUID_TYPE(as_uuid=True), nullable=True)  # Correlation ID for tracking requests
    
    # Status and result
    status = Column(String(50), default="success", nullable=False)  # success, failure, partial
    http_status_code = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Detailed information
    details = Column(JSON, default=dict, nullable=False)  # Additional context
    # Example: {
    #   "changes": {"field": {"old": old_value, "new": new_value}},
    #   "reason": "User requested cancellation",
    #   "metadata": {...}
    # }
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Indexes
    __table_args__ = (
        Index("idx_audit_logs_tenant_created", "tenant_id", "created_at"),
        Index("idx_audit_logs_resource", "tenant_id", "resource_type", "resource_id"),
        Index("idx_audit_logs_actor", "tenant_id", "actor_user_id"),
        Index("idx_audit_logs_action", "action"),
        Index("idx_audit_logs_created", "created_at"),
    )
