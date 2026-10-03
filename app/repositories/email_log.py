"""Repository for email logs"""

from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.email_log import EmailLog
from app.core.exceptions import ResourceNotFoundException


class EmailLogRepository:
    """Repository for EmailLog operations"""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
    
    def get_by_id(self, log_id: str, tenant_id: str) -> EmailLog:
        """Get email log by ID (tenant-scoped)"""
        log = self.db_session.query(EmailLog).filter_by(
            id=log_id,
            tenant_id=tenant_id
        ).first()
        if not log:
            raise ResourceNotFoundException(f"Email log {log_id} not found")
        return log
    
    def list_by_tenant(self, tenant_id: str, status: Optional[str] = None) -> List[EmailLog]:
        """List email logs for tenant"""
        query = self.db_session.query(EmailLog).filter_by(tenant_id=tenant_id)
        if status:
            query = query.filter_by(status=status)
        return query.order_by(EmailLog.created_at.desc()).all()
    
    def list_pending_retry(self) -> List[EmailLog]:
        """List emails pending retry"""
        return self.db_session.query(EmailLog).filter(
            EmailLog.status == "failed",
            EmailLog.retry_count < EmailLog.max_retries,
            EmailLog.next_retry_at <= datetime.utcnow()
        ).all()
    
    def create(self, log_data: dict) -> EmailLog:
        """Create a new email log entry"""
        log = EmailLog(**log_data)
        self.db_session.add(log)
        self.db_session.flush()
        return log
    
    def update(self, log_id: str, tenant_id: str, log_data: dict) -> EmailLog:
        """Update an email log"""
        log = self.get_by_id(log_id, tenant_id)
        for key, value in log_data.items():
            setattr(log, key, value)
        self.db_session.flush()
        return log
    
    def mark_sent(self, log_id: str, tenant_id: str, message_id: Optional[str] = None) -> EmailLog:
        """Mark email as sent"""
        log = self.get_by_id(log_id, tenant_id)
        log.status = "sent"
        log.sent_at = datetime.utcnow()
        if message_id:
            log.provider_message_id = message_id
        self.db_session.flush()
        return log
    
    def mark_failed(self, log_id: str, tenant_id: str, error: str) -> EmailLog:
        """Mark email as failed"""
        log = self.get_by_id(log_id, tenant_id)
        log.status = "failed"
        log.error_message = error
        log.retry_count += 1
        log.last_retry_at = datetime.utcnow()
        
        # Schedule next retry (exponential backoff: 1h, 6h, 24h)
        retry_delays = [1, 6, 24]  # hours
        if log.retry_count <= len(retry_delays):
            next_retry_hours = retry_delays[log.retry_count - 1]
            log.next_retry_at = datetime.utcnow() + timedelta(hours=next_retry_hours)
        
        self.db_session.flush()
        return log
    
    def cleanup_old_logs(self, older_than_days: int = 90) -> int:
        """Delete old email logs (keep audit trail for specified days)"""
        cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)
        deleted_count = self.db_session.query(EmailLog).filter(
            EmailLog.created_at < cutoff_date,
            EmailLog.status.in_(["sent", "bounced"])
        ).delete()
        self.db_session.flush()
        return deleted_count
