"""Phase 7: Advanced Features - Webhooks, Audit Logs, Data Exports"""

import pytest
import json
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

from app.models.webhook import WebhookEndpoint, WebhookDelivery, WebhookEventType
from app.models.audit_log import AuditLog, AuditAction
from app.models.data_export import DataExport, DataExportStatus
from app.repositories.webhook import WebhookEndpointRepository, WebhookDeliveryRepository
from app.repositories.audit_log import AuditLogRepository
from app.repositories.data_export import DataExportRepository
from app.services.webhook import WebhookService
from app.services.audit import AuditService
from app.services.data_export import DataExportService
from app.core.utils import generate_id


class TestWebhookEndpoint:
    """Webhook endpoint tests"""
    
    def test_create_webhook_endpoint(self, db: Session):
        """Test creating a webhook endpoint"""
        repo = WebhookEndpointRepository(db)
        
        endpoint = repo.create(
            tenant_id="tenant1",
            name="Test Webhook",
            url="https://example.com/webhooks",
            events=["user.created", "subscription.upgraded"],
            description="Test endpoint",
        )
        
        assert endpoint.id
        assert endpoint.name == "Test Webhook"
        assert endpoint.url == "https://example.com/webhooks"
        assert "user.created" in endpoint.events
        assert endpoint.is_active == True
        assert len(endpoint.secret) > 20
    
    def test_get_webhook_endpoint(self, db: Session):
        """Test retrieving a webhook endpoint"""
        repo = WebhookEndpointRepository(db)
        
        endpoint = repo.create(
            tenant_id="tenant1",
            name="Test Webhook",
            url="https://example.com/webhooks",
            events=["invoice.paid"],
        )
        
        retrieved = repo.get_by_id("tenant1", endpoint.id)
        assert retrieved.id == endpoint.id
        assert retrieved.name == "Test Webhook"
    
    def test_list_webhook_endpoints(self, db: Session):
        """Test listing webhook endpoints"""
        repo = WebhookEndpointRepository(db)
        
        # Create multiple endpoints
        for i in range(3):
            repo.create(
                tenant_id="tenant1",
                name=f"Webhook {i}",
                url=f"https://example.com/webhook{i}",
                events=["user.created"],
            )
        
        endpoints = repo.list_by_tenant("tenant1")
        assert len(endpoints) == 3
    
    def test_update_webhook_endpoint(self, db: Session):
        """Test updating a webhook endpoint"""
        repo = WebhookEndpointRepository(db)
        
        endpoint = repo.create(
            tenant_id="tenant1",
            name="Test Webhook",
            url="https://example.com/webhooks",
            events=["user.created"],
        )
        
        updated = repo.update(
            tenant_id="tenant1",
            endpoint_id=endpoint.id,
            name="Updated Webhook",
            is_active=False,
        )
        
        assert updated.name == "Updated Webhook"
        assert updated.is_active == False
    
    def test_delete_webhook_endpoint(self, db: Session):
        """Test deleting a webhook endpoint"""
        repo = WebhookEndpointRepository(db)
        
        endpoint = repo.create(
            tenant_id="tenant1",
            name="Test Webhook",
            url="https://example.com/webhooks",
            events=["user.created"],
        )
        
        deleted = repo.delete("tenant1", endpoint.id)
        assert deleted == True
        
        retrieved = repo.get_by_id("tenant1", endpoint.id)
        assert retrieved is None
    
    def test_webhook_event_filtering(self, db: Session):
        """Test webhook event filtering logic"""
        repo = WebhookEndpointRepository(db)
        
        # Endpoint with specific events
        endpoint = repo.create(
            tenant_id="tenant1",
            name="Invoice Webhook",
            url="https://example.com/webhooks",
            events=["invoice.paid", "invoice.failed"],
        )
        
        assert endpoint.should_deliver_event("invoice.paid") == True
        assert endpoint.should_deliver_event("invoice.failed") == True
        assert endpoint.should_deliver_event("user.created") == False
    
    def test_webhook_wildcard_events(self, db: Session):
        """Test webhook with wildcard events"""
        repo = WebhookEndpointRepository(db)
        
        # Endpoint with wildcard
        endpoint = repo.create(
            tenant_id="tenant1",
            name="Catch All Webhook",
            url="https://example.com/webhooks",
            events=["*"],
        )
        
        assert endpoint.should_deliver_event("invoice.paid") == True
        assert endpoint.should_deliver_event("user.created") == True
        assert endpoint.should_deliver_event("subscription.upgraded") == True
    
    def test_webhook_signature_generation(self, db: Session):
        """Test HMAC signature generation"""
        repo = WebhookEndpointRepository(db)
        
        endpoint = repo.create(
            tenant_id="tenant1",
            name="Test Webhook",
            url="https://example.com/webhooks",
            events=["user.created"],
            secret="test-secret-key",
        )
        
        payload = '{"id": "test", "type": "user.created"}'
        signature = endpoint.get_signature(payload)
        
        assert isinstance(signature, str)
        assert len(signature) == 64  # SHA256 hex is 64 chars


class TestWebhookDelivery:
    """Webhook delivery tests"""
    
    def test_create_webhook_delivery(self, db: Session):
        """Test creating a webhook delivery record"""
        repo_endpoint = WebhookEndpointRepository(db)
        repo_delivery = WebhookDeliveryRepository(db)
        
        endpoint = repo_endpoint.create(
            tenant_id="tenant1",
            name="Test",
            url="https://example.com",
            events=["user.created"],
        )
        
        delivery = repo_delivery.create(
            endpoint_id=endpoint.id,
            event_type="user.created",
            event_id="user-123",
            payload={"id": "user-123", "email": "test@example.com"},
        )
        
        assert delivery.id
        assert delivery.status == "pending"
        assert delivery.attempt_count == 0
    
    def test_webhook_delivery_retry_logic(self, db: Session):
        """Test webhook delivery retry logic"""
        repo_endpoint = WebhookEndpointRepository(db)
        repo_delivery = WebhookDeliveryRepository(db)
        
        endpoint = repo_endpoint.create(
            tenant_id="tenant1",
            name="Test",
            url="https://example.com",
            events=["user.created"],
            retry_delay_seconds=300,
        )
        
        delivery = repo_delivery.create(
            endpoint_id=endpoint.id,
            event_type="user.created",
            event_id="user-123",
            payload={},
            max_attempts=3,
        )
        
        # First failure
        delivery.mark_failed("Connection timeout")
        assert delivery.attempt_count == 1
        assert delivery.status == "failed"
        assert delivery.next_retry_at is not None
        
        # Second failure
        delivery.mark_failed("Connection timeout")
        assert delivery.attempt_count == 2
        assert delivery.status == "failed"
        
        # Third failure - exhausted
        delivery.mark_failed("Connection timeout")
        assert delivery.attempt_count == 3
        assert delivery.status == "exhausted"
    
    def test_mark_delivery_sent(self, db: Session):
        """Test marking delivery as sent"""
        repo_endpoint = WebhookEndpointRepository(db)
        repo_delivery = WebhookDeliveryRepository(db)
        
        endpoint = repo_endpoint.create(
            tenant_id="tenant1",
            name="Test",
            url="https://example.com",
            events=["user.created"],
        )
        
        delivery = repo_delivery.create(
            endpoint_id=endpoint.id,
            event_type="user.created",
            event_id="user-123",
            payload={},
        )
        
        delivery.mark_sent(200, '{"success": true}')
        
        assert delivery.status == "sent"
        assert delivery.http_status_code == 200
        assert delivery.completed_at is not None
    
    def test_list_ready_for_retry(self, db: Session):
        """Test finding deliveries ready for retry"""
        repo_endpoint = WebhookEndpointRepository(db)
        repo_delivery = WebhookDeliveryRepository(db)
        
        endpoint = repo_endpoint.create(
            tenant_id="tenant1",
            name="Test",
            url="https://example.com",
            events=["user.created"],
            retry_delay_seconds=0,  # No delay for testing
        )
        
        # Create pending delivery
        delivery1 = repo_delivery.create(
            endpoint_id=endpoint.id,
            event_type="user.created",
            event_id="user-1",
            payload={},
        )
        
        # Create completed delivery
        delivery2 = repo_delivery.create(
            endpoint_id=endpoint.id,
            event_type="user.created",
            event_id="user-2",
            payload={},
        )
        delivery2.mark_sent(200)
        
        ready = repo_delivery.list_ready_for_retry(limit=10)
        assert len(ready) == 1
        assert ready[0].id == delivery1.id


class TestAuditLog:
    """Audit log tests"""
    
    def test_create_audit_log(self, db: Session):
        """Test creating an audit log entry"""
        repo = AuditLogRepository(db)
        
        log = repo.create(
            tenant_id="tenant1",
            action=AuditAction.USER_CREATED,
            resource_type="user",
            resource_id="user-123",
            actor_user_id="admin-1",
            status="success",
        )
        
        assert log.id
        assert log.action == AuditAction.USER_CREATED
        assert log.resource_type == "user"
        assert log.status == "success"
    
    def test_list_audit_logs(self, db: Session):
        """Test listing audit logs"""
        repo = AuditLogRepository(db)
        
        # Create multiple logs
        for i in range(3):
            repo.create(
                tenant_id="tenant1",
                action=AuditAction.USER_CREATED,
                resource_type="user",
                resource_id=f"user-{i}",
                actor_user_id="admin-1",
            )
        
        logs, total = repo.list_for_tenant("tenant1", limit=10)
        assert len(logs) == 3
        assert total == 3
    
    def test_list_audit_logs_by_action(self, db: Session):
        """Test filtering audit logs by action"""
        repo = AuditLogRepository(db)
        
        # Create different types of logs
        repo.create(
            tenant_id="tenant1",
            action=AuditAction.USER_CREATED,
            resource_type="user",
        )
        repo.create(
            tenant_id="tenant1",
            action=AuditAction.LOGIN,
            resource_type="user",
        )
        
        logs, total = repo.list_for_tenant(
            "tenant1",
            action=AuditAction.LOGIN,
        )
        assert len(logs) == 1
        assert logs[0].action == AuditAction.LOGIN
    
    def test_audit_log_resource_tracking(self, db: Session):
        """Test listing logs for a specific resource"""
        repo = AuditLogRepository(db)
        
        # Create logs for same resource
        for i in range(3):
            repo.create(
                tenant_id="tenant1",
                action=AuditAction.USER_UPDATED,
                resource_type="user",
                resource_id="user-123",
                actor_user_id=f"admin-{i}",
            )
        
        logs = repo.list_for_resource(
            "tenant1",
            "user",
            "user-123",
        )
        assert len(logs) == 3
    
    def test_audit_log_with_changes(self, db: Session):
        """Test audit log with change tracking"""
        repo = AuditLogRepository(db)
        
        changes = {
            "name": {"old": "John", "new": "Jane"},
            "email": {"old": "john@example.com", "new": "jane@example.com"},
        }
        
        log = repo.create(
            tenant_id="tenant1",
            action=AuditAction.USER_UPDATED,
            resource_type="user",
            resource_id="user-123",
            actor_user_id="admin-1",
            details={"changes": changes},
        )
        
        assert log.details["changes"]["name"]["old"] == "John"
        assert log.details["changes"]["name"]["new"] == "Jane"
    
    def test_audit_service_convenience_methods(self, db: Session):
        """Test AuditService convenience methods"""
        service = AuditService(db)
        
        log = service.log_user_created(
            tenant_id="tenant1",
            user_id="user-123",
            actor_user_id="admin-1",
        )
        
        assert log.action == AuditAction.USER_CREATED
        assert log.resource_id == "user-123"


class TestDataExport:
    """Data export tests"""
    
    def test_create_data_export(self, db: Session):
        """Test creating a data export request"""
        repo = DataExportRepository(db)
        
        export = repo.create(
            tenant_id="tenant1",
            format="json",
            requested_by="user-1",
            include_users=True,
            include_subscriptions=True,
        )
        
        assert export.id
        assert export.status == DataExportStatus.PENDING
        assert export.format == "json"
        assert export.requested_by == "user-1"
    
    def test_list_data_exports(self, db: Session):
        """Test listing data exports"""
        repo = DataExportRepository(db)
        
        for i in range(3):
            repo.create(
                tenant_id="tenant1",
                format="json",
                requested_by="user-1",
            )
        
        exports, total = repo.list_for_tenant("tenant1")
        assert len(exports) == 3
        assert total == 3
    
    def test_mark_export_completed(self, db: Session):
        """Test marking export as completed"""
        repo = DataExportRepository(db)
        
        export = repo.create(
            tenant_id="tenant1",
            format="json",
            requested_by="user-1",
        )
        
        completed = repo.mark_completed(
            export.id,
            file_path="/exports/export-123.json",
            file_name="export.json",
            file_size_bytes=1024000,
            total_records=500,
        )
        
        assert completed.status == DataExportStatus.COMPLETED
        assert completed.file_size_bytes == 1024000
        assert completed.total_records == 500
        assert completed.download_token is not None
        assert completed.download_token_expires_at is not None
    
    def test_mark_export_failed(self, db: Session):
        """Test marking export as failed"""
        repo = DataExportRepository(db)
        
        export = repo.create(
            tenant_id="tenant1",
            format="json",
            requested_by="user-1",
        )
        
        failed = repo.mark_failed(export.id, "Database connection error")
        
        assert failed.status == DataExportStatus.FAILED
        assert failed.error_message == "Database connection error"
        assert failed.completed_at is not None
    
    def test_soft_delete_export(self, db: Session):
        """Test soft delete of export"""
        repo = DataExportRepository(db)
        
        export = repo.create(
            tenant_id="tenant1",
            format="json",
            requested_by="user-1",
        )
        
        deleted = repo.soft_delete(export.id)
        assert deleted == True
        
        # Verify soft deleted
        result = repo.get_by_id("tenant1", export.id)
        # Should still exist but marked deleted
        if result:
            assert result.is_deleted == True
    
    def test_download_token_expiry(self, db: Session):
        """Test download token expiration"""
        repo = DataExportRepository(db)
        
        export = repo.create(
            tenant_id="tenant1",
            format="json",
            requested_by="user-1",
        )
        
        completed = repo.mark_completed(
            export.id,
            file_path="/exports/export-123.json",
            file_name="export.json",
            file_size_bytes=1024000,
            total_records=500,
        )
        
        # Should be available immediately
        assert completed.is_download_available() == True
        
        # Simulate token expiry
        completed.download_token_expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        
        # Should not be available now
        assert completed.is_download_available() == False
    
    def test_record_download(self, db: Session):
        """Test recording download actions"""
        repo = DataExportRepository(db)
        
        export = repo.create(
            tenant_id="tenant1",
            format="json",
            requested_by="user-1",
        )
        
        completed = repo.mark_completed(
            export.id,
            file_path="/exports/export-123.json",
            file_name="export.json",
            file_size_bytes=1024000,
            total_records=500,
        )
        
        # Record multiple downloads
        repo.record_download(export.id)
        repo.record_download(export.id)
        
        updated = repo.get_by_id("tenant1", export.id)
        assert updated.download_count == 2


# Test fixtures
@pytest.fixture
def db():
    """Create a test database session"""
    from app.database import SessionLocal
    session = SessionLocal()
    yield session
    session.close()
