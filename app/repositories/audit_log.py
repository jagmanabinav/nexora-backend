from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.audit_log import AuditLog, AuditAction
from uuid import uuid4 as generate_id


class AuditLogRepository:
    """Repository for audit logs"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create(
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
        details: dict = None,
    ) -> AuditLog:
        """Create an audit log entry"""
        audit = AuditLog(
            id=generate_id(),
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
            details=details or {},
        )
        
        self.session.add(audit)
        self.session.flush()
        return audit
    
    def get_by_id(self, tenant_id: str, audit_id: str) -> Optional[AuditLog]:
        """Get audit log by ID"""
        return self.session.query(AuditLog).filter(
            AuditLog.tenant_id == tenant_id,
            AuditLog.id == audit_id,
        ).first()
    
    def list_for_tenant(
        self,
        tenant_id: str,
        limit: int = 100,
        offset: int = 0,
        action: str = None,
        resource_type: str = None,
        actor_user_id: str = None,
        created_after: datetime = None,
        created_before: datetime = None,
    ) -> tuple[List[AuditLog], int]:
        """List audit logs for a tenant with filtering"""
        query = self.session.query(AuditLog).filter(
            AuditLog.tenant_id == tenant_id
        )
        
        if action:
            query = query.filter(AuditLog.action == action)
        if resource_type:
            query = query.filter(AuditLog.resource_type == resource_type)
        if actor_user_id:
            query = query.filter(AuditLog.actor_user_id == actor_user_id)
        if created_after:
            query = query.filter(AuditLog.created_at >= created_after)
        if created_before:
            query = query.filter(AuditLog.created_at <= created_before)
        
        total = query.count()
        
        logs = query.order_by(
            AuditLog.created_at.desc()
        ).offset(offset).limit(limit).all()
        
        return logs, total
    
    def list_for_resource(
        self,
        tenant_id: str,
        resource_type: str,
        resource_id: str,
        limit: int = 100,
    ) -> List[AuditLog]:
        """List all audit logs for a specific resource"""
        return self.session.query(AuditLog).filter(
            AuditLog.tenant_id == tenant_id,
            AuditLog.resource_type == resource_type,
            AuditLog.resource_id == resource_id,
        ).order_by(AuditLog.created_at.desc()).limit(limit).all()
    
    def list_by_actor(
        self,
        tenant_id: str,
        actor_user_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[List[AuditLog], int]:
        """List audit logs by actor with pagination"""
        query = self.session.query(AuditLog).filter(
            AuditLog.tenant_id == tenant_id,
            AuditLog.actor_user_id == actor_user_id,
        )
        
        total = query.count()
        
        logs = query.order_by(
            AuditLog.created_at.desc()
        ).offset(offset).limit(limit).all()
        
        return logs, total
    
    def cleanup_old_logs(self, days_to_keep: int = 90) -> int:
        """Delete audit logs older than the specified days"""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
        
        result = self.session.query(AuditLog).filter(
            AuditLog.created_at < cutoff_date
        ).delete(synchronize_session=False)
        
        self.session.flush()
        return result
