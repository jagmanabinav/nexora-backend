from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from app.models.audit_log import AuditLog, AuditAction
from app.repositories.audit_log import AuditLogRepository


class AuditService:
    """Service for audit logging"""
    
    def __init__(self, session):
        self.session = session
        self.repo = AuditLogRepository(session)
    
    def log_action(
        self,
        tenant_id: str,
        action: str,
        resource_type: str,
        resource_id: str = None,
        actor_user_id: str = None,
        actor_type: str = "user",
        actor_ip: str = None,
        actor_user_agent: str = None,
        request_method: str = None,
        request_path: str = None,
        request_id: str = None,
        status: str = "success",
        http_status_code: int = None,
        error_message: str = None,
        changes: Dict[str, Any] = None,
        metadata: Dict[str, Any] = None,
    ) -> AuditLog:
        """Log an audit action"""
        details = {}
        
        if changes:
            details["changes"] = changes
        if metadata:
            details["metadata"] = metadata
        
        return self.repo.create(
            tenant_id=tenant_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            actor_user_id=actor_user_id,
            actor_type=actor_type,
            actor_ip=actor_ip,
            actor_user_agent=actor_user_agent,
            request_method=request_method,
            request_path=request_path,
            request_id=request_id,
            status=status,
            http_status_code=http_status_code,
            error_message=error_message,
            details=details,
        )
    
    def log_user_created(
        self,
        tenant_id: str,
        user_id: str,
        actor_user_id: str,
        **kwargs
    ) -> AuditLog:
        """Log user creation"""
        return self.log_action(
            tenant_id=tenant_id,
            action=AuditAction.USER_CREATED,
            resource_type="user",
            resource_id=user_id,
            actor_user_id=actor_user_id,
            **kwargs
        )
    
    def log_user_updated(
        self,
        tenant_id: str,
        user_id: str,
        actor_user_id: str,
        changes: Dict = None,
        **kwargs
    ) -> AuditLog:
        """Log user update"""
        return self.log_action(
            tenant_id=tenant_id,
            action=AuditAction.USER_UPDATED,
            resource_type="user",
            resource_id=user_id,
            actor_user_id=actor_user_id,
            changes=changes,
            **kwargs
        )
    
    def log_user_deleted(
        self,
        tenant_id: str,
        user_id: str,
        actor_user_id: str,
        **kwargs
    ) -> AuditLog:
        """Log user deletion"""
        return self.log_action(
            tenant_id=tenant_id,
            action=AuditAction.USER_DELETED,
            resource_type="user",
            resource_id=user_id,
            actor_user_id=actor_user_id,
            **kwargs
        )
    
    def log_login(
        self,
        tenant_id: str,
        user_id: str,
        actor_ip: str = None,
        actor_user_agent: str = None,
        **kwargs
    ) -> AuditLog:
        """Log successful login"""
        return self.log_action(
            tenant_id=tenant_id,
            action=AuditAction.LOGIN,
            resource_type="user",
            resource_id=user_id,
            actor_user_id=user_id,
            actor_ip=actor_ip,
            actor_user_agent=actor_user_agent,
            **kwargs
        )
    
    def log_login_failed(
        self,
        tenant_id: str,
        email: str,
        actor_ip: str = None,
        actor_user_agent: str = None,
        error_message: str = None,
        **kwargs
    ) -> AuditLog:
        """Log failed login attempt"""
        return self.log_action(
            tenant_id=tenant_id,
            action=AuditAction.LOGIN_FAILED,
            resource_type="user",
            actor_type="anonymous",
            actor_ip=actor_ip,
            actor_user_agent=actor_user_agent,
            status="failure",
            error_message=error_message,
            metadata={"email": email},
            **kwargs
        )
    
    def log_subscription_created(
        self,
        tenant_id: str,
        subscription_id: str,
        actor_user_id: str,
        plan_id: str = None,
        **kwargs
    ) -> AuditLog:
        """Log subscription creation"""
        return self.log_action(
            tenant_id=tenant_id,
            action=AuditAction.SUBSCRIPTION_CREATED,
            resource_type="subscription",
            resource_id=subscription_id,
            actor_user_id=actor_user_id,
            metadata={"plan_id": plan_id},
            **kwargs
        )
    
    def log_subscription_upgraded(
        self,
        tenant_id: str,
        subscription_id: str,
        actor_user_id: str,
        old_plan_id: str = None,
        new_plan_id: str = None,
        **kwargs
    ) -> AuditLog:
        """Log subscription upgrade"""
        return self.log_action(
            tenant_id=tenant_id,
            action=AuditAction.SUBSCRIPTION_UPGRADED,
            resource_type="subscription",
            resource_id=subscription_id,
            actor_user_id=actor_user_id,
            changes={
                "plan": {"old": old_plan_id, "new": new_plan_id}
            },
            **kwargs
        )
    
    def log_subscription_cancelled(
        self,
        tenant_id: str,
        subscription_id: str,
        actor_user_id: str,
        reason: str = None,
        **kwargs
    ) -> AuditLog:
        """Log subscription cancellation"""
        return self.log_action(
            tenant_id=tenant_id,
            action=AuditAction.SUBSCRIPTION_CANCELLED,
            resource_type="subscription",
            resource_id=subscription_id,
            actor_user_id=actor_user_id,
            metadata={"reason": reason} if reason else {},
            **kwargs
        )
    
    def log_invoice_paid(
        self,
        tenant_id: str,
        invoice_id: str,
        actor_user_id: str = None,
        amount: float = None,
        **kwargs
    ) -> AuditLog:
        """Log invoice payment"""
        return self.log_action(
            tenant_id=tenant_id,
            action=AuditAction.INVOICE_PAID,
            resource_type="invoice",
            resource_id=invoice_id,
            actor_user_id=actor_user_id,
            actor_type="system" if not actor_user_id else "user",
            metadata={"amount": amount},
            **kwargs
        )
    
    def log_api_key_created(
        self,
        tenant_id: str,
        api_key_id: str,
        actor_user_id: str,
        **kwargs
    ) -> AuditLog:
        """Log API key creation"""
        return self.log_action(
            tenant_id=tenant_id,
            action=AuditAction.API_KEY_CREATED,
            resource_type="api_key",
            resource_id=api_key_id,
            actor_user_id=actor_user_id,
            **kwargs
        )
    
    def log_api_key_deleted(
        self,
        tenant_id: str,
        api_key_id: str,
        actor_user_id: str,
        **kwargs
    ) -> AuditLog:
        """Log API key deletion"""
        return self.log_action(
            tenant_id=tenant_id,
            action=AuditAction.API_KEY_DELETED,
            resource_type="api_key",
            resource_id=api_key_id,
            actor_user_id=actor_user_id,
            **kwargs
        )
    
    def log_webhook_created(
        self,
        tenant_id: str,
        webhook_id: str,
        actor_user_id: str,
        **kwargs
    ) -> AuditLog:
        """Log webhook creation"""
        return self.log_action(
            tenant_id=tenant_id,
            action=AuditAction.WEBHOOK_CREATED,
            resource_type="webhook",
            resource_id=webhook_id,
            actor_user_id=actor_user_id,
            **kwargs
        )
    
    def log_webhook_deleted(
        self,
        tenant_id: str,
        webhook_id: str,
        actor_user_id: str,
        **kwargs
    ) -> AuditLog:
        """Log webhook deletion"""
        return self.log_action(
            tenant_id=tenant_id,
            action=AuditAction.WEBHOOK_DELETED,
            resource_type="webhook",
            resource_id=webhook_id,
            actor_user_id=actor_user_id,
            **kwargs
        )
    
    def log_data_export_requested(
        self,
        tenant_id: str,
        export_id: str,
        actor_user_id: str,
        format: str = None,
        **kwargs
    ) -> AuditLog:
        """Log data export request"""
        return self.log_action(
            tenant_id=tenant_id,
            action=AuditAction.DATA_EXPORT_REQUESTED,
            resource_type="data_export",
            resource_id=export_id,
            actor_user_id=actor_user_id,
            metadata={"format": format},
            **kwargs
        )
    
    def log_data_export_completed(
        self,
        tenant_id: str,
        export_id: str,
        record_count: int = None,
        **kwargs
    ) -> AuditLog:
        """Log data export completion"""
        return self.log_action(
            tenant_id=tenant_id,
            action=AuditAction.DATA_EXPORT_COMPLETED,
            resource_type="data_export",
            resource_id=export_id,
            actor_type="system",
            metadata={"record_count": record_count},
            **kwargs
        )
    
    def get_audit_log(self, tenant_id: str, audit_id: str) -> Optional[AuditLog]:
        """Get an audit log entry"""
        return self.repo.get_by_id(tenant_id, audit_id)
    
    def list_audit_logs(
        self,
        tenant_id: str,
        action: str = None,
        resource_type: str = None,
        actor_user_id: str = None,
        created_after: datetime = None,
        created_before: datetime = None,
        limit: int = 100,
        offset: int = 0,
    ):
        """List audit logs for a tenant"""
        return self.repo.list_for_tenant(
            tenant_id=tenant_id,
            action=action,
            resource_type=resource_type,
            actor_user_id=actor_user_id,
            created_after=created_after,
            created_before=created_before,
            limit=limit,
            offset=offset,
        )
    
    def cleanup_old_logs(self, days_to_keep: int = 90) -> int:
        """Delete old audit logs"""
        return self.repo.cleanup_old_logs(days_to_keep)
