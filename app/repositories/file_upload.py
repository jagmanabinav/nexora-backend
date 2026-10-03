"""Repository for file uploads"""

from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.file_upload import FileUpload
from app.core.exceptions import ResourceNotFoundException


class FileUploadRepository:
    """Repository for FileUpload operations"""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
    
    def get_by_id(self, file_id: str, tenant_id: str) -> FileUpload:
        """Get file upload by ID (tenant-scoped)"""
        file = self.db_session.query(FileUpload).filter_by(
            id=file_id,
            tenant_id=tenant_id,
            is_deleted=0
        ).first()
        if not file:
            raise ResourceNotFoundException(f"File {file_id} not found")
        return file
    
    def get_by_key(self, file_key: str, tenant_id: str) -> Optional[FileUpload]:
        """Get file by storage key (tenant-scoped)"""
        return self.db_session.query(FileUpload).filter_by(
            file_key=file_key,
            tenant_id=tenant_id,
            is_deleted=0
        ).first()
    
    def list_by_tenant(self, tenant_id: str) -> List[FileUpload]:
        """List all files for tenant"""
        return self.db_session.query(FileUpload).filter_by(
            tenant_id=tenant_id,
            is_deleted=0
        ).order_by(FileUpload.created_at.desc()).all()
    
    def list_by_bucket(self, tenant_id: str, bucket: str) -> List[FileUpload]:
        """List files in a specific bucket"""
        return self.db_session.query(FileUpload).filter_by(
            tenant_id=tenant_id,
            bucket=bucket,
            is_deleted=0
        ).order_by(FileUpload.created_at.desc()).all()
    
    def get_total_storage_used(self, tenant_id: str) -> int:
        """Get total storage used by tenant (in bytes)"""
        result = self.db_session.query(func.sum(FileUpload.file_size)).filter_by(
            tenant_id=tenant_id,
            is_deleted=0
        ).scalar()
        return result or 0
    
    def create(self, file_data: dict) -> FileUpload:
        """Create a new file upload record"""
        file = FileUpload(**file_data)
        self.db_session.add(file)
        self.db_session.flush()
        return file
    
    def update(self, file_id: str, tenant_id: str, file_data: dict) -> FileUpload:
        """Update a file upload record"""
        file = self.get_by_id(file_id, tenant_id)
        for key, value in file_data.items():
            setattr(file, key, value)
        self.db_session.flush()
        return file
    
    def soft_delete(self, file_id: str, tenant_id: str) -> FileUpload:
        """Soft delete a file (mark as deleted)"""
        file = self.get_by_id(file_id, tenant_id)
        file.is_deleted = 1
        file.deleted_at = datetime.utcnow()
        self.db_session.flush()
        return file
    
    def cleanup_deleted_files(self, older_than_days: int = 30) -> int:
        """Permanently delete files marked as deleted"""
        from datetime import timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)
        deleted_count = self.db_session.query(FileUpload).filter(
            FileUpload.is_deleted == 1,
            FileUpload.deleted_at < cutoff_date
        ).delete()
        self.db_session.flush()
        return deleted_count
