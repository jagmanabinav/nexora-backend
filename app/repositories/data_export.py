from typing import List, Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.data_export import DataExport, DataExportStatus, DataExportFormat
from uuid import uuid4 as generate_id
import secrets


class DataExportRepository:
    """Repository for data exports"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create(
        self,
        tenant_id: str,
        format: str,
        requested_by: str,
        include_users: bool = True,
        include_subscriptions: bool = True,
        include_invoices: bool = True,
        include_audit_logs: bool = False,
        include_usage_data: bool = True,
        include_api_keys: bool = False,
        include_webhook_events: bool = False,
        created_from: datetime = None,
        created_to: datetime = None,
    ) -> DataExport:
        """Create a new data export request"""
        export = DataExport(
            id=uuid4(),
            tenant_id=tenant_id,
            format=format,
            requested_by=requested_by,
            include_users=include_users,
            include_subscriptions=include_subscriptions,
            include_invoices=include_invoices,
            include_audit_logs=include_audit_logs,
            include_usage_data=include_usage_data,
            include_api_keys=include_api_keys,
            include_webhook_events=include_webhook_events,
            created_from=created_from,
            created_to=created_to,
            status=DataExportStatus.PENDING,
        )
        
        self.session.add(export)
        self.session.flush()
        return export
    
    def get_by_id(self, tenant_id: str, export_id: str) -> Optional[DataExport]:
        """Get data export by ID"""
        return self.session.query(DataExport).filter(
            DataExport.tenant_id == tenant_id,
            DataExport.id == export_id,
        ).first()
    
    def get_by_download_token(self, download_token: str) -> Optional[DataExport]:
        """Get data export by download token"""
        return self.session.query(DataExport).filter(
            DataExport.download_token == download_token,
            DataExport.status == DataExportStatus.COMPLETED,
        ).first()
    
    def list_for_tenant(
        self,
        tenant_id: str,
        status: str = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[List[DataExport], int]:
        """List data exports for a tenant"""
        query = self.session.query(DataExport).filter(
            DataExport.tenant_id == tenant_id,
            DataExport.is_deleted == False,
        )
        
        if status:
            query = query.filter(DataExport.status == status)
        
        total = query.count()
        
        exports = query.order_by(
            DataExport.created_at.desc()
        ).offset(offset).limit(limit).all()
        
        return exports, total
    
    def list_pending(self, limit: int = 100) -> List[DataExport]:
        """List all pending export requests"""
        return self.session.query(DataExport).filter(
            DataExport.status == DataExportStatus.PENDING,
        ).order_by(DataExport.created_at.asc()).limit(limit).all()
    
    def list_processing(self, limit: int = 100) -> List[DataExport]:
        """List all currently processing exports"""
        return self.session.query(DataExport).filter(
            DataExport.status == DataExportStatus.PROCESSING,
        ).order_by(DataExport.created_at.asc()).limit(limit).all()
    
    def update_status(
        self,
        export_id: str,
        status: str,
        error_message: str = None,
    ) -> Optional[DataExport]:
        """Update export status"""
        export = self.session.query(DataExport).filter(
            DataExport.id == export_id
        ).first()
        
        if not export:
            return None
        
        export.status = status
        if error_message:
            export.error_message = error_message
        
        if status == DataExportStatus.COMPLETED:
            export.completed_at = datetime.now(timezone.utc)
        
        self.session.flush()
        return export
    
    def mark_completed(
        self,
        export_id: str,
        file_path: str,
        file_name: str,
        file_size_bytes: int,
        total_records: int,
    ) -> Optional[DataExport]:
        """Mark export as completed"""
        export = self.session.query(DataExport).filter(
            DataExport.id == export_id
        ).first()
        
        if not export:
            return None
        
        # Generate download token
        download_token = secrets.token_urlsafe(32)
        
        export.status = DataExportStatus.COMPLETED
        export.file_path = file_path
        export.file_name = file_name
        export.file_size_bytes = file_size_bytes
        export.total_records = total_records
        export.download_token = download_token
        export.download_token_expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        export.expires_at = datetime.now(timezone.utc) + timedelta(days=30)
        export.completed_at = datetime.now(timezone.utc)
        
        self.session.flush()
        return export
    
    def mark_failed(
        self,
        export_id: str,
        error_message: str,
    ) -> Optional[DataExport]:
        """Mark export as failed"""
        export = self.session.query(DataExport).filter(
            DataExport.id == export_id
        ).first()
        
        if not export:
            return None
        
        export.status = DataExportStatus.FAILED
        export.error_message = error_message
        export.completed_at = datetime.now(timezone.utc)
        
        self.session.flush()
        return export
    
    def record_download(self, export_id: str) -> bool:
        """Record a download action"""
        export = self.session.query(DataExport).filter(
            DataExport.id == export_id
        ).first()
        
        if not export:
            return False
        
        export.record_download()
        self.session.flush()
        return True
    
    def soft_delete(self, export_id: str) -> bool:
        """Soft delete an export"""
        export = self.session.query(DataExport).filter(
            DataExport.id == export_id
        ).first()
        
        if not export:
            return False
        
        export.is_deleted = True
        export.deleted_at = datetime.now(timezone.utc)
        
        self.session.flush()
        return True
    
    def cleanup_expired_exports(self) -> int:
        """Delete expired exports (older than expiry date)"""
        now = datetime.now(timezone.utc)
        
        result = self.session.query(DataExport).filter(
            DataExport.expires_at <= now,
        ).delete(synchronize_session=False)
        
        self.session.flush()
        return result
    
    def cleanup_old_requests(self, days_to_keep: int = 90) -> int:
        """Delete old soft-deleted export requests"""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
        
        result = self.session.query(DataExport).filter(
            DataExport.is_deleted == True,
            DataExport.deleted_at < cutoff_date,
        ).delete(synchronize_session=False)
        
        self.session.flush()
        return result
