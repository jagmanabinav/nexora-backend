from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Optional
from datetime import datetime

from app.core.dependencies import get_current_user, get_request_context, RequestContext
from app.schemas.advanced import (
    WebhookEndpointCreate, WebhookEndpointUpdate, WebhookEndpointResponse,
    WebhookDeliveriesListResponse, AuditLogResponse, AuditLogsListResponse,
    AuditLogsFilterParams, DataExportCreate, DataExportResponse,
    DataExportListResponse, DataExportDownloadResponse,
)
from app.services.webhook import WebhookService
from app.services.audit import AuditService
from app.services.data_export import DataExportService
from app.core.dependencies import get_db_session
from sqlalchemy.orm import Session

router = APIRouter(tags=["advanced"])


# ============ WEBHOOK ENDPOINTS ============

@router.post("/webhooks", response_model=WebhookEndpointResponse, status_code=status.HTTP_201_CREATED)
def create_webhook_endpoint(
    payload: WebhookEndpointCreate,
    current_user = Depends(get_current_user),
    context: RequestContext = Depends(get_request_context),
    session: Session = Depends(get_db_session),
):
    """Create a new webhook endpoint"""
    service = WebhookService(session)
    
    endpoint = service.create_endpoint(
        tenant_id=context.tenant_id,
        name=payload.name,
        url=payload.url,
        events=payload.events,
        description=payload.description,
        headers=payload.headers,
    )
    
    session.commit()
    
    # Audit log
    audit = AuditService(session)
    audit.log_webhook_created(
        tenant_id=context.tenant_id,
        webhook_id=str(endpoint.id),
        actor_user_id=current_user.user_id,
        request_path=context.request_path,
        request_method=context.request_method,
    )
    session.commit()
    
    return WebhookEndpointResponse.model_validate(endpoint)


@router.get("/webhooks", response_model=list[WebhookEndpointResponse])
def list_webhook_endpoints(
    current_user = Depends(get_current_user),
    context: RequestContext = Depends(get_request_context),
    session: Session = Depends(get_db_session),
):
    """List all webhook endpoints for the tenant"""
    service = WebhookService(session)
    endpoints = service.list_endpoints(context.tenant_id)
    return [WebhookEndpointResponse.model_validate(e) for e in endpoints]


@router.get("/webhooks/{endpoint_id}", response_model=WebhookEndpointResponse)
def get_webhook_endpoint(
    endpoint_id: str,
    current_user = Depends(get_current_user),
    context: RequestContext = Depends(get_request_context),
    session: Session = Depends(get_db_session),
):
    """Get a specific webhook endpoint"""
    service = WebhookService(session)
    endpoint = service.get_endpoint(context.tenant_id, endpoint_id)
    
    if not endpoint:
        raise HTTPException(status_code=404, detail="Webhook endpoint not found")
    
    return WebhookEndpointResponse.model_validate(endpoint)


@router.put("/webhooks/{endpoint_id}", response_model=WebhookEndpointResponse)
def update_webhook_endpoint(
    endpoint_id: str,
    payload: WebhookEndpointUpdate,
    current_user = Depends(get_current_user),
    context: RequestContext = Depends(get_request_context),
    session: Session = Depends(get_db_session),
):
    """Update a webhook endpoint"""
    service = WebhookService(session)
    
    endpoint = service.update_endpoint(
        tenant_id=context.tenant_id,
        endpoint_id=endpoint_id,
        name=payload.name,
        url=payload.url,
        events=payload.events,
        description=payload.description,
        is_active=payload.is_active,
        headers=payload.headers,
    )
    
    if not endpoint:
        raise HTTPException(status_code=404, detail="Webhook endpoint not found")
    
    session.commit()
    return WebhookEndpointResponse.model_validate(endpoint)


@router.delete("/webhooks/{endpoint_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_webhook_endpoint(
    endpoint_id: str,
    current_user = Depends(get_current_user),
    context: RequestContext = Depends(get_request_context),
    session: Session = Depends(get_db_session),
):
    """Delete a webhook endpoint"""
    service = WebhookService(session)
    
    if not service.delete_endpoint(context.tenant_id, endpoint_id):
        raise HTTPException(status_code=404, detail="Webhook endpoint not found")
    
    session.commit()
    
    # Audit log
    audit = AuditService(session)
    audit.log_webhook_deleted(
        tenant_id=context.tenant_id,
        webhook_id=endpoint_id,
        actor_user_id=current_user.user_id,
        request_path=context.request_path,
        request_method=context.request_method,
    )
    session.commit()


@router.get("/webhooks/{endpoint_id}/deliveries", response_model=WebhookDeliveriesListResponse)
def list_webhook_deliveries(
    endpoint_id: str,
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user = Depends(get_current_user),
    context: RequestContext = Depends(get_request_context),
    session: Session = Depends(get_db_session),
):
    """List webhook deliveries for an endpoint"""
    service = WebhookService(session)
    
    # Verify endpoint exists and belongs to tenant
    endpoint = service.get_endpoint(context.tenant_id, endpoint_id)
    if not endpoint:
        raise HTTPException(status_code=404, detail="Webhook endpoint not found")
    
    deliveries, total = service.get_deliveries(
        endpoint_id=endpoint_id,
        status=status,
        limit=limit,
        offset=offset,
    )
    
    return WebhookDeliveriesListResponse(
        deliveries=[d for d in deliveries],  # Convert ORM to schema
        total=total,
        limit=limit,
        offset=offset,
    )


# ============ AUDIT LOG ENDPOINTS ============

@router.get("/audit-logs", response_model=AuditLogsListResponse)
def list_audit_logs(
    action: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    actor_user_id: Optional[str] = Query(None),
    created_after: Optional[datetime] = Query(None),
    created_before: Optional[datetime] = Query(None),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user = Depends(get_current_user),
    context: RequestContext = Depends(get_request_context),
    session: Session = Depends(get_db_session),
):
    """List audit logs for the tenant"""
    service = AuditService(session)
    logs, total = service.list_audit_logs(
        tenant_id=context.tenant_id,
        action=action,
        resource_type=resource_type,
        actor_user_id=actor_user_id,
        created_after=created_after,
        created_before=created_before,
        limit=limit,
        offset=offset,
    )
    
    return AuditLogsListResponse(
        logs=[AuditLogResponse.model_validate(l) for l in logs],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/audit-logs/{audit_id}", response_model=AuditLogResponse)
def get_audit_log(
    audit_id: str,
    current_user = Depends(get_current_user),
    context: RequestContext = Depends(get_request_context),
    session: Session = Depends(get_db_session),
):
    """Get a specific audit log entry"""
    service = AuditService(session)
    log = service.get_audit_log(context.tenant_id, audit_id)
    
    if not log:
        raise HTTPException(status_code=404, detail="Audit log not found")
    
    return AuditLogResponse.model_validate(log)


# ============ DATA EXPORT ENDPOINTS ============

@router.post("/data-exports", response_model=DataExportResponse, status_code=status.HTTP_201_CREATED)
def create_data_export(
    payload: DataExportCreate,
    current_user = Depends(get_current_user),
    context: RequestContext = Depends(get_request_context),
    session: Session = Depends(get_db_session),
):
    """Create a new data export request"""
    service = DataExportService(session)
    
    export = service.create_export(
        tenant_id=context.tenant_id,
        requested_by=current_user.user_id,
        format=payload.format,
        include_users=payload.include_users,
        include_subscriptions=payload.include_subscriptions,
        include_invoices=payload.include_invoices,
        include_audit_logs=payload.include_audit_logs,
        include_usage_data=payload.include_usage_data,
        include_api_keys=payload.include_api_keys,
        include_webhook_events=payload.include_webhook_events,
        created_from=payload.created_from,
        created_to=payload.created_to,
    )
    
    session.commit()
    
    # Audit log
    audit = AuditService(session)
    audit.log_data_export_requested(
        tenant_id=context.tenant_id,
        export_id=str(export.id),
        actor_user_id=current_user.user_id,
        format=payload.format,
        request_path=context.request_path,
        request_method=context.request_method,
    )
    session.commit()
    
    return DataExportResponse.model_validate(export)


@router.get("/data-exports", response_model=DataExportListResponse)
def list_data_exports(
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user = Depends(get_current_user),
    context: RequestContext = Depends(get_request_context),
    session: Session = Depends(get_db_session),
):
    """List data exports for the tenant"""
    service = DataExportService(session)
    exports, total = service.list_exports(
        tenant_id=context.tenant_id,
        status=status,
        limit=limit,
        offset=offset,
    )
    
    return DataExportListResponse(
        exports=[DataExportResponse.model_validate(e) for e in exports],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/data-exports/{export_id}", response_model=DataExportResponse)
def get_data_export(
    export_id: str,
    current_user = Depends(get_current_user),
    context: RequestContext = Depends(get_request_context),
    session: Session = Depends(get_db_session),
):
    """Get a specific data export"""
    service = DataExportService(session)
    export = service.get_export(context.tenant_id, export_id)
    
    if not export:
        raise HTTPException(status_code=404, detail="Data export not found")
    
    return DataExportResponse.model_validate(export)


@router.get("/data-exports/{export_id}/download-url", response_model=DataExportDownloadResponse)
def get_data_export_download_url(
    export_id: str,
    current_user = Depends(get_current_user),
    context: RequestContext = Depends(get_request_context),
    session: Session = Depends(get_db_session),
):
    """Get download URL for a completed export"""
    service = DataExportService(session)
    export = service.get_export(context.tenant_id, export_id)
    
    if not export:
        raise HTTPException(status_code=404, detail="Data export not found")
    
    if export.status != "completed":
        raise HTTPException(status_code=400, detail="Export not yet completed")
    
    if not export.is_download_available():
        raise HTTPException(status_code=410, detail="Download link expired")
    
    return DataExportDownloadResponse(
        download_url=export.get_download_url("http://localhost:8000"),  # Use configured API URL
        expires_in_hours=7,
        file_size_bytes=export.file_size_bytes,
        format=export.format,
    )


@router.delete("/data-exports/{export_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_data_export(
    export_id: str,
    current_user = Depends(get_current_user),
    context: RequestContext = Depends(get_request_context),
    session: Session = Depends(get_db_session),
):
    """Delete (soft-delete) a data export"""
    service = DataExportService(session)
    export = service.get_export(context.tenant_id, export_id)
    
    if not export:
        raise HTTPException(status_code=404, detail="Data export not found")
    
    service.repo.soft_delete(export_id)
    session.commit()
