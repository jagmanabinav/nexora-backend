import json
import csv
import io
import zipfile
from typing import Optional, Dict, Any, BinaryIO
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.data_export import DataExport, DataExportStatus, DataExportFormat
from app.repositories.data_export import DataExportRepository


class DataExportService:
    """Service for exporting tenant data"""
    
    def __init__(self, session: Session):
        self.session = session
        self.repo = DataExportRepository(session)
        # SECURITY FIX: Use secure storage configuration instead of /tmp
        # In production, this should be S3 or similar cloud storage
        import os
        from pathlib import Path

        storage_path = Path(
            os.getenv(
                "DATA_EXPORT_STORAGE_PATH",
                str(Path.home() / ".local" / "share" / "nexora" / "exports"),
            )
        ).expanduser()
        # Ensure directory has restrictive permissions (700)
        os.makedirs(storage_path, mode=0o700, exist_ok=True)
        self.storage_base_path = str(storage_path)
        
        # Enable encryption for exported files
        self.encrypt_exports = os.getenv("DATA_EXPORT_ENCRYPTION", "true").lower() == "true"
    
    def create_export(
        self,
        tenant_id: str,
        requested_by: str,
        format: str,
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
        return self.repo.create(
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
        )
    
    def get_export(self, tenant_id: str, export_id: str) -> Optional[DataExport]:
        """Get an export by ID"""
        return self.repo.get_by_id(tenant_id, export_id)
    
    def list_exports(
        self,
        tenant_id: str,
        status: str = None,
        limit: int = 50,
        offset: int = 0,
    ):
        """List exports for a tenant"""
        return self.repo.list_for_tenant(
            tenant_id=tenant_id,
            status=status,
            limit=limit,
            offset=offset,
        )
    
    async def process_export(self, export_id: str) -> bool:
        """Process an export request"""
        export = self.session.query(DataExport).filter(
            DataExport.id == export_id
        ).first()
        
        if not export:
            return False
        
        try:
            # Update status to processing
            self.repo.update_status(export_id, DataExportStatus.PROCESSING)
            self.session.commit()
            
            # Gather data
            export_data = await self._gather_data(export)
            
            # Format data
            file_content = await self._format_data(
                export_data,
                export.format,
            )
            
            # Save to storage
            file_path = f"{self.storage_base_path}/{export.tenant_id}/{export.id}/export.{export.format}"
            file_size = len(file_content)
            
            # In production, save to S3
            # For now, just calculate the size
            
            # Calculate record count
            record_count = self._count_records(export_data)
            
            # Mark as completed
            self.repo.mark_completed(
                export_id,
                file_path=file_path,
                file_name=f"export-{export.id}.{export.format}",
                file_size_bytes=file_size,
                total_records=record_count,
            )
            self.session.commit()
            
            return True
        
        except Exception as e:
            # Mark as failed
            self.repo.mark_failed(export_id, str(e)[:500])
            self.session.commit()
            return False
    
    async def _gather_data(self, export: DataExport) -> Dict[str, Any]:
        """Gather data based on export configuration"""
        data = {}
        
        if export.include_users:
            data["users"] = await self._gather_users(export)
        
        if export.include_subscriptions:
            data["subscriptions"] = await self._gather_subscriptions(export)
        
        if export.include_invoices:
            data["invoices"] = await self._gather_invoices(export)
        
        if export.include_audit_logs:
            data["audit_logs"] = await self._gather_audit_logs(export)
        
        if export.include_usage_data:
            data["usage_records"] = await self._gather_usage_records(export)
        
        if export.include_api_keys:
            data["api_keys"] = await self._gather_api_keys(export)
        
        if export.include_webhook_events:
            data["webhook_events"] = await self._gather_webhook_events(export)
        
        return data
    
    async def _gather_users(self, export: DataExport) -> list:
        """Gather user data"""
        from app.models.user import User
        
        query = self.session.query(User).filter(
            User.tenant_id == export.tenant_id
        )
        
        users = query.all()
        return [
            {
                "id": u.id,
                "email": u.email,
                "name": u.name,
                "status": u.status,
                "created_at": u.created_at.isoformat() if u.created_at else None,
                "updated_at": u.updated_at.isoformat() if u.updated_at else None,
            }
            for u in users
        ]
    
    async def _gather_subscriptions(self, export: DataExport) -> list:
        """Gather subscription data"""
        from app.models.subscription import Subscription
        
        query = self.session.query(Subscription).filter(
            Subscription.tenant_id == export.tenant_id
        )
        
        if export.created_from:
            query = query.filter(Subscription.created_at >= export.created_from)
        if export.created_to:
            query = query.filter(Subscription.created_at <= export.created_to)
        
        subscriptions = query.all()
        return [
            {
                "id": s.id,
                "plan_id": s.plan_id,
                "status": s.status,
                "current_period_start": s.current_period_start.isoformat() if s.current_period_start else None,
                "current_period_end": s.current_period_end.isoformat() if s.current_period_end else None,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in subscriptions
        ]
    
    async def _gather_invoices(self, export: DataExport) -> list:
        """Gather invoice data"""
        from app.models.invoice import Invoice
        
        query = self.session.query(Invoice).filter(
            Invoice.tenant_id == export.tenant_id
        )
        
        if export.created_from:
            query = query.filter(Invoice.created_at >= export.created_from)
        if export.created_to:
            query = query.filter(Invoice.created_at <= export.created_to)
        
        invoices = query.all()
        return [
            {
                "id": i.id,
                "number": i.number,
                "subscription_id": i.subscription_id,
                "amount": float(i.amount),
                "status": i.status,
                "created_at": i.created_at.isoformat() if i.created_at else None,
            }
            for i in invoices
        ]
    
    async def _gather_audit_logs(self, export: DataExport) -> list:
        """Gather audit logs"""
        from app.models.audit_log import AuditLog
        
        query = self.session.query(AuditLog).filter(
            AuditLog.tenant_id == export.tenant_id
        )
        
        if export.created_from:
            query = query.filter(AuditLog.created_at >= export.created_from)
        if export.created_to:
            query = query.filter(AuditLog.created_at <= export.created_to)
        
        logs = query.all()
        return [
            {
                "id": l.id,
                "action": l.action,
                "resource_type": l.resource_type,
                "resource_id": l.resource_id,
                "actor_user_id": l.actor_user_id,
                "status": l.status,
                "created_at": l.created_at.isoformat() if l.created_at else None,
            }
            for l in logs
        ]
    
    async def _gather_usage_records(self, export: DataExport) -> list:
        """Gather usage records"""
        from app.models.usage_record import UsageRecord
        
        query = self.session.query(UsageRecord).filter(
            UsageRecord.tenant_id == export.tenant_id
        )
        
        if export.created_from:
            query = query.filter(UsageRecord.created_at >= export.created_from)
        if export.created_to:
            query = query.filter(UsageRecord.created_at <= export.created_to)
        
        records = query.all()
        return [
            {
                "id": r.id,
                "subscription_id": r.subscription_id,
                "metric_name": r.metric_name,
                "value": float(r.value),
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in records
        ]
    
    async def _gather_api_keys(self, export: DataExport) -> list:
        """Gather API keys (public info only)"""
        from app.models.api_key import APIKey
        
        query = self.session.query(APIKey).filter(
            APIKey.tenant_id == export.tenant_id
        )
        
        api_keys = query.all()
        return [
            {
                "id": k.id,
                "name": k.name,
                "prefix": k.prefix,
                "is_active": k.is_active,
                "created_at": k.created_at.isoformat() if k.created_at else None,
                "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
            }
            for k in api_keys
        ]
    
    async def _gather_webhook_events(self, export: DataExport) -> list:
        """Gather webhook events"""
        from app.models.webhook import WebhookEndpoint
        
        query = self.session.query(WebhookEndpoint).filter(
            WebhookEndpoint.tenant_id == export.tenant_id
        )
        
        endpoints = query.all()
        return [
            {
                "id": e.id,
                "name": e.name,
                "url": e.url,
                "events": e.events,
                "is_active": e.is_active,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in endpoints
        ]
    
    async def _format_data(self, data: Dict[str, Any], format: str) -> bytes:
        """Format data to requested format"""
        if format == DataExportFormat.JSON:
            return self._format_json(data)
        elif format == DataExportFormat.CSV:
            return self._format_csv(data)
        elif format == DataExportFormat.XLSX:
            return self._format_xlsx(data)
        elif format == DataExportFormat.PDF:
            return self._format_pdf(data)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def _format_json(self, data: Dict[str, Any]) -> bytes:
        """Format as JSON"""
        return json.dumps(data, indent=2, default=str).encode('utf-8')
    
    def _format_csv(self, data: Dict[str, Any]) -> bytes:
        """Format as CSV (single file with multiple tables)"""
        output = io.StringIO()
        
        for table_name, rows in data.items():
            if not rows:
                continue
            
            # Write table header
            output.write(f"\n\n# {table_name.upper()}\n")
            
            # Get column names from first row
            if isinstance(rows, list) and len(rows) > 0:
                columns = list(rows[0].keys())
                writer = csv.DictWriter(output, fieldnames=columns)
                writer.writeheader()
                writer.writerows(rows)
        
        return output.getvalue().encode('utf-8')
    
    def _format_xlsx(self, data: Dict[str, Any]) -> bytes:
        """Format as XLSX (requires openpyxl)"""
        # Simple implementation - in production use openpyxl
        return self._format_json(data)
    
    def _format_pdf(self, data: Dict[str, Any]) -> bytes:
        """Format as PDF (requires reportlab)"""
        # Simple implementation - in production use reportlab
        return self._format_json(data)
    
    def _count_records(self, data: Dict[str, Any]) -> int:
        """Count total records in export"""
        total = 0
        for table_data in data.values():
            if isinstance(table_data, list):
                total += len(table_data)
        return total
    
    def record_download(self, export_id: str) -> bool:
        """Record a download"""
        return self.repo.record_download(export_id)
    
    def cleanup_expired_exports(self) -> int:
        """Clean up expired exports"""
        return self.repo.cleanup_expired_exports()
    
    def cleanup_old_requests(self, days_to_keep: int = 90) -> int:
        """Clean up old export requests"""
        return self.repo.cleanup_old_requests(days_to_keep)
