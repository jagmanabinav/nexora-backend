from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


# ============ WEBHOOK SCHEMAS ============

class WebhookEventType(str, Enum):
    """Webhook event types"""
    USER_CREATED = "user.created"
    SUBSCRIPTION_CREATED = "subscription.created"
    SUBSCRIPTION_UPGRADED = "subscription.upgraded"
    SUBSCRIPTION_CANCELLED = "subscription.cancelled"
    INVOICE_CREATED = "invoice.created"
    INVOICE_PAID = "invoice.paid"
    INVOICE_FAILED = "invoice.failed"


class WebhookEndpointCreate(BaseModel):
    """Create webhook endpoint"""
    name: str = Field(..., min_length=1, max_length=255)
    url: str = Field(..., description="Webhook URL")
    description: Optional[str] = Field(None, max_length=1000)
    events: List[str] = Field(default=[], description="List of event types to subscribe to")
    headers: Optional[Dict[str, str]] = Field(default=None, description="Custom headers")


class WebhookEndpointUpdate(BaseModel):
    """Update webhook endpoint"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    url: Optional[str] = None
    description: Optional[str] = Field(None, max_length=1000)
    events: Optional[List[str]] = None
    is_active: Optional[bool] = None
    headers: Optional[Dict[str, str]] = None


class WebhookEndpointResponse(BaseModel):
    """Webhook endpoint response"""
    id: str
    name: str
    url: str
    description: Optional[str]
    is_active: bool
    events: List[str]
    secret: str
    created_at: datetime
    updated_at: datetime


class WebhookDeliveryResponse(BaseModel):
    """Webhook delivery record"""
    id: str
    endpoint_id: str
    event_type: str
    event_id: str
    status: str
    http_status_code: Optional[int]
    error_message: Optional[str]
    attempt_count: int
    max_attempts: int
    last_attempted_at: Optional[datetime]
    next_retry_at: Optional[datetime]
    created_at: datetime
    completed_at: Optional[datetime]


class WebhookDeliveriesListResponse(BaseModel):
    """Paginated webhook deliveries"""
    deliveries: List[WebhookDeliveryResponse]
    total: int
    limit: int
    offset: int


# ============ AUDIT LOG SCHEMAS ============

class AuditLogCreate(BaseModel):
    """Create audit log entry"""
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    changes: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class AuditLogResponse(BaseModel):
    """Audit log response"""
    id: str
    action: str
    resource_type: str
    resource_id: Optional[str]
    actor_user_id: Optional[str]
    actor_type: str
    actor_ip: Optional[str]
    status: str
    http_status_code: Optional[int]
    error_message: Optional[str]
    details: Dict[str, Any]
    created_at: datetime


class AuditLogsListResponse(BaseModel):
    """Paginated audit logs"""
    logs: List[AuditLogResponse]
    total: int
    limit: int
    offset: int


class AuditLogsFilterParams(BaseModel):
    """Audit log filtering parameters"""
    action: Optional[str] = None
    resource_type: Optional[str] = None
    actor_user_id: Optional[str] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    limit: int = Field(default=50, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)


# ============ DATA EXPORT SCHEMAS ============

class DataExportFormat(str, Enum):
    """Data export formats"""
    JSON = "json"
    CSV = "csv"
    XLSX = "xlsx"
    PDF = "pdf"


class DataExportCreate(BaseModel):
    """Create data export request"""
    format: str = Field(..., description="Export format: json, csv, xlsx, pdf")
    include_users: bool = Field(default=True)
    include_subscriptions: bool = Field(default=True)
    include_invoices: bool = Field(default=True)
    include_audit_logs: bool = Field(default=False)
    include_usage_data: bool = Field(default=True)
    include_api_keys: bool = Field(default=False)
    include_webhook_events: bool = Field(default=False)
    created_from: Optional[datetime] = None
    created_to: Optional[datetime] = None


class DataExportResponse(BaseModel):
    """Data export response"""
    id: str
    format: str
    status: str
    total_records: Optional[int]
    file_size_bytes: Optional[int]
    file_name: Optional[str]
    download_count: int
    error_message: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]
    expires_at: Optional[datetime]


class DataExportListResponse(BaseModel):
    """Paginated data exports"""
    exports: List[DataExportResponse]
    total: int
    limit: int
    offset: int


class DataExportDownloadResponse(BaseModel):
    """Download URL for export"""
    download_url: str
    expires_in_hours: int
    file_size_bytes: int
    format: str
