from uuid import uuid4
from sqlalchemy.dialects.postgresql import UUID as UUID_TYPE
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Index, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.base import Base, TimestampedModel


class FileUpload(TimestampedModel):
    """Track uploaded files and metadata"""
    
    __tablename__ = "file_uploads"
    __allow_unmapped__ = True
    
    tenant_id = Column(UUID_TYPE(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # File details
    filename = Column(String(500), nullable=False)
    file_key = Column(String(1000), nullable=False, unique=True)  # S3 key or path
    file_size = Column(Integer, nullable=False)  # bytes
    mime_type = Column(String(100), nullable=False)  # application/pdf, image/png, etc.
    
    # Storage details
    storage_provider = Column(String(50), nullable=False)  # s3, gcs, local
    bucket = Column(String(255), nullable=False)
    
    # Metadata
    description = Column(Text, nullable=True)
    is_public = Column(Integer, default=0)  # 1 = public, 0 = private (tenant-scoped)
    
    # Checksums for integrity
    md5_hash = Column(String(32), nullable=True)
    
    # Lifecycle
    is_deleted = Column(Integer, default=0)  # soft delete
    deleted_at = Column(DateTime, nullable=True)
    
    # Relationships
    tenant = relationship("Tenant")
    
    __table_args__ = (
        Index("idx_tenant_created_date", "tenant_id", "created_at"),
        Index("idx_file_key", "file_key"),
    )
    
    def __repr__(self):
        return f"<FileUpload(id={self.id}, filename={self.filename}, size={self.file_size})>"
    
    @property
    def size_mb(self) -> float:
        """Return file size in MB"""
        return self.file_size / (1024 * 1024)
