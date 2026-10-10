from enum import Enum
from uuid import uuid4
from sqlalchemy.dialects.postgresql import UUID as UUID_TYPE
from sqlalchemy import String, DateTime, Text, Integer, Boolean, Column, Index, ForeignKey
from datetime import datetime, timezone

from app.models.base import Base


class DataExportFormat(str, Enum):
    """Data export formats"""
    JSON = "json"
    CSV = "csv"
    XLSX = "xlsx"
    PDF = "pdf"


class DataExportStatus(str, Enum):
    """Data export status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class DataExport(Base):
    """User/tenant data export requests"""
    
    __tablename__ = "data_exports"
    __allow_unmapped__ = True

    id = Column(UUID_TYPE(as_uuid=True), primary_key=True, default=uuid4, nullable=False)
    tenant_id = Column(
        UUID_TYPE(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Request info
    format = Column(String(50), nullable=False)  # json, csv, xlsx, pdf
    status = Column(String(50), default="pending", nullable=False)
    
    # Data scope
    include_users = Column(Boolean, default=True, nullable=False)
    include_subscriptions = Column(Boolean, default=True, nullable=False)
    include_invoices = Column(Boolean, default=True, nullable=False)
    include_audit_logs = Column(Boolean, default=False, nullable=False)
    include_usage_data = Column(Boolean, default=True, nullable=False)
    include_api_keys = Column(Boolean, default=False, nullable=False)
    include_webhook_events = Column(Boolean, default=False, nullable=False)
    
    # Filtering
    created_from = Column(DateTime(timezone=True), nullable=True)  # Export data created after this date
    created_to = Column(DateTime(timezone=True), nullable=True)    # Export data created before this date
    
    # Actor info
    requested_by = Column(UUID_TYPE(as_uuid=True), nullable=False)  # User ID who requested the export
    
    # Processing info
    file_path = Column(String(500), nullable=True)  # Path to exported file
    file_size_bytes = Column(Integer, nullable=True)  # Size of exported file
    file_name = Column(String(255), nullable=True)  # Friendly file name
    
    # Download tracking
    download_token = Column(String(255), nullable=True)  # Secure token for download
    download_token_expires_at = Column(DateTime(timezone=True), nullable=True)
    download_count = Column(Integer, default=0, nullable=False)
    last_downloaded_at = Column(DateTime(timezone=True), nullable=True)
    
    # Data summary
    total_records = Column(Integer, nullable=True)  # Total records in export
    error_message = Column(Text, nullable=True)  # Error message if export failed
    
    # Cleanup tracking
    expires_at = Column(DateTime(timezone=True), nullable=True)  # When to delete the export file
    is_deleted = Column(Boolean, default=False, nullable=False)  # Soft delete flag
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Indexes
    __table_args__ = (
        Index("idx_data_exports_tenant_status", "tenant_id", "status"),
        Index("idx_data_exports_expires", "expires_at"),
        Index("idx_data_exports_requested_by", "requested_by"),
        Index("idx_data_exports_created", "created_at"),
    )
    
    def get_download_url(self, api_url: str) -> str:
        """Generate download URL for the export"""
        return f"{api_url}/data-exports/{self.id}/download?token={self.download_token}"
    
    def is_download_available(self) -> bool:
        """Check if export can still be downloaded"""
        if self.status != DataExportStatus.COMPLETED.value:
            return False
        if self.is_deleted:
            return False
        if self.download_token_expires_at and datetime.now(timezone.utc) > self.download_token_expires_at:
            return False
        return True
    
    def record_download(self):
        """Record a download action"""
        self.download_count += 1
        self.last_downloaded_at = datetime.now(timezone.utc)
