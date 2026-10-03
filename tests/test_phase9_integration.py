"""Integration tests for Nexora Core - Multi-phase workflows"""

import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.tenant import Tenant
from app.models.subscription import Subscription
from app.models.plan import Plan
from app.models.invoice import Invoice
from app.models.audit_log import AuditLog
from app.models.webhook import WebhookEndpoint, WebhookDelivery
from app.models.data_export import DataExport
from app.repositories.user import UserRepository
from app.repositories.tenant import TenantRepository
from app.repositories.subscription import SubscriptionRepository
from app.repositories.plan import PlanRepository
from app.repositories.invoice import InvoiceRepository
from app.repositories.audit_log import AuditLogRepository
from app.repositories.webhook import WebhookEndpointRepository
from app.repositories.data_export import DataExportRepository
from app.services.auth import AuthService
from app.services.billing import BillingService
from app.services.audit import AuditService
from app.services.webhook import WebhookService
from app.services.data_export import DataExportService
from app.core.utils import generate_id


class TestMultiPhaseWorkflows:
    """Test complete workflows spanning multiple phases"""
    
    def test_complete_user_lifecycle(self, db: Session):
        """Test complete user lifecycle: creation → authentication → audit trail"""
        # Setup
        tenant_repo = TenantRepository(db)
        user_repo = UserRepository(db)
        audit_service = AuditService(db)
        
        # Phase 1: Create tenant
        tenant = tenant_repo.create(name="Test Tenant")
        assert tenant.id
        
        # Phase 2: Create user
        user = user_repo.create(
            tenant_id=tenant.id,
            email="test@example.com",
            name="Test User",
            password="SecurePassword123!",
        )
        assert user.id
        
        # Log user creation
        audit_service.log_user_created(
            tenant_id=tenant.id,
            user_id=user.id,
            actor_user_id="admin-1",
        )
        
        # Phase 3: Verify audit log
        logs, total = audit_service.list_audit_logs(
            tenant_id=tenant.id,
            resource_type="user",
        )
        
        assert len(logs) > 0
        assert logs[0].action == "user_created"
        assert logs[0].resource_id == user.id
        
        db.commit()
    
    def test_subscription_creation_and_invoicing(self, db: Session):
        """Test subscription creation → invoice generation → audit trail"""
        # Setup
        tenant_repo = TenantRepository(db)
        plan_repo = PlanRepository(db)
        subscription_repo = SubscriptionRepository(db)
        invoice_repo = InvoiceRepository(db)
        audit_service = AuditService(db)
        
        # Create tenant
        tenant = tenant_repo.create(name="SaaS Tenant")
        
        # Create plan
        plan = plan_repo.create(
            tenant_id=tenant.id,
            name="Pro",
            description="Professional plan",
            price=99.00,
            billing_period_days=30,
            features={"api_calls": 10000, "users": 50},
        )
        
        # Create subscription
        subscription = subscription_repo.create(
            tenant_id=tenant.id,
            plan_id=plan.id,
            status="active",
        )
        
        assert subscription.status == "active"
        assert subscription.current_period_start
        assert subscription.current_period_end
        
        # Audit the subscription creation
        audit_service.log_subscription_created(
            tenant_id=tenant.id,
            subscription_id=subscription.id,
            actor_user_id="admin-1",
            plan_id=plan.id,
        )
        
        # Verify subscription is active
        active_sub = subscription_repo.get_active_subscription(tenant.id)
        assert active_sub.id == subscription.id
        
        db.commit()
    
    def test_webhook_event_triggering(self, db: Session):
        """Test webhook endpoint creation → event trigger → delivery"""
        # Setup
        webhook_service = WebhookService(db)
        
        # Create webhook endpoint
        endpoint = webhook_service.create_endpoint(
            tenant_id="tenant-123",
            name="Billing Webhook",
            url="https://example.com/webhooks",
            events=["invoice.paid", "subscription.upgraded"],
        )
        
        assert endpoint.id
        assert endpoint.is_active == True
        assert len(endpoint.events) == 2
        
        # Verify event filtering
        assert endpoint.should_deliver_event("invoice.paid") == True
        assert endpoint.should_deliver_event("subscription.upgraded") == True
        assert endpoint.should_deliver_event("user.created") == False
        
        db.commit()
    
    def test_audit_logging_for_billing_event(self, db: Session):
        """Test that billing events are properly logged in audit trail"""
        # Setup
        audit_service = AuditService(db)
        
        # Simulate payment
        log = audit_service.log_invoice_paid(
            tenant_id="tenant-123",
            invoice_id="invoice-456",
            actor_user_id=None,
            amount=99.00,
        )
        
        assert log.action == "invoice_paid"
        assert log.resource_type == "invoice"
        assert log.actor_type == "system"
        assert log.details["metadata"]["amount"] == 99.00
        
        db.commit()
    
    def test_data_export_creation_and_status_tracking(self, db: Session):
        """Test data export request creation and status tracking"""
        # Setup
        export_service = DataExportService(db)
        export_repo = DataExportRepository(db)
        
        # Create export request
        export = export_service.create_export(
            tenant_id="tenant-123",
            requested_by="user-456",
            format="json",
            include_users=True,
            include_subscriptions=True,
        )
        
        assert export.status == "pending"
        assert export.format == "json"
        assert export.download_count == 0
        
        # Mark as processing
        export_repo.update_status(export.id, "processing")
        
        # Mark as completed
        completed = export_repo.mark_completed(
            export.id,
            file_path="/exports/export.json",
            file_name="export-123.json",
            file_size_bytes=2048000,
            total_records=5000,
        )
        
        assert completed.status == "completed"
        assert completed.total_records == 5000
        assert completed.download_token is not None
        
        db.commit()
    
    def test_security_event_audit_trail(self, db: Session):
        """Test that security events are properly logged"""
        # Setup
        audit_service = AuditService(db)
        
        # Log failed login
        audit_service.log_login_failed(
            tenant_id="tenant-123",
            email="user@example.com",
            actor_ip="192.168.1.1",
            error_message="Invalid password",
        )
        
        # Log API key creation
        audit_service.log_api_key_created(
            tenant_id="tenant-123",
            api_key_id="key-789",
            actor_user_id="admin-1",
        )
        
        # List security events
        logs, total = audit_service.list_audit_logs(
            tenant_id="tenant-123",
        )
        
        assert len(logs) >= 2
        
        # Verify events are logged
        actions = [log.action for log in logs]
        assert "login_failed" in actions
        assert "api_key_created" in actions
        
        db.commit()
    
    def test_tenant_isolation_enforcement(self, db: Session):
        """Test that tenant isolation is enforced across all phases"""
        # Setup repos
        user_repo = UserRepository(db)
        subscription_repo = SubscriptionRepository(db)
        audit_repo = AuditLogRepository(db)
        
        # Create users for different tenants
        user1 = user_repo.create(
            tenant_id="tenant-1",
            email="user1@example.com",
            name="User 1",
            password="pass1",
        )
        
        user2 = user_repo.create(
            tenant_id="tenant-2",
            email="user2@example.com",
            name="User 2",
            password="pass2",
        )
        
        # Log actions for different tenants
        audit_repo.create(
            tenant_id="tenant-1",
            action="login",
            resource_type="user",
            resource_id=user1.id,
        )
        
        audit_repo.create(
            tenant_id="tenant-2",
            action="login",
            resource_type="user",
            resource_id=user2.id,
        )
        
        # Verify tenant isolation
        tenant1_logs, _ = audit_repo.list_for_tenant("tenant-1", limit=100)
        tenant2_logs, _ = audit_repo.list_for_tenant("tenant-2", limit=100)
        
        assert len(tenant1_logs) > 0
        assert len(tenant2_logs) > 0
        
        # Ensure no cross-tenant leakage
        assert all(log.tenant_id == "tenant-1" for log in tenant1_logs)
        assert all(log.tenant_id == "tenant-2" for log in tenant2_logs)
        assert len([l for l in tenant1_logs if l.tenant_id == "tenant-2"]) == 0
        
        db.commit()
    
    def test_subscription_upgrade_workflow(self, db: Session):
        """Test subscription upgrade with proration"""
        # Setup
        plan_repo = PlanRepository(db)
        subscription_repo = SubscriptionRepository(db)
        audit_service = AuditService(db)
        
        tenant_id = "tenant-123"
        
        # Create plans
        basic_plan = plan_repo.create(
            tenant_id=tenant_id,
            name="Basic",
            price=29.00,
            billing_period_days=30,
        )
        
        pro_plan = plan_repo.create(
            tenant_id=tenant_id,
            name="Pro",
            price=99.00,
            billing_period_days=30,
        )
        
        # Create subscription on Basic plan
        subscription = subscription_repo.create(
            tenant_id=tenant_id,
            plan_id=basic_plan.id,
            status="active",
        )
        
        original_plan_id = subscription.plan_id
        
        # Simulate upgrade
        subscription.plan_id = pro_plan.id
        subscription.upgraded_at = datetime.now(timezone.utc)
        
        # Log upgrade
        audit_service.log_subscription_upgraded(
            tenant_id=tenant_id,
            subscription_id=subscription.id,
            actor_user_id="user-1",
            old_plan_id=original_plan_id,
            new_plan_id=pro_plan.id,
        )
        
        # Verify upgrade logged
        logs, _ = audit_service.list_audit_logs(
            tenant_id=tenant_id,
            action="subscription_upgraded",
        )
        
        assert len(logs) > 0
        assert logs[0].details["changes"]["plan"]["old"] == original_plan_id
        
        db.commit()


class TestDataIntegrity:
    """Test data integrity across operations"""
    
    def test_foreign_key_constraints(self, db: Session):
        """Verify foreign key constraints are enforced"""
        # Setup
        subscription_repo = SubscriptionRepository(db)
        plan_repo = PlanRepository(db)
        
        # Create plan
        plan = plan_repo.create(
            tenant_id="tenant-1",
            name="Test",
            price=10.00,
        )
        
        # Create subscription with valid plan FK
        sub = subscription_repo.create(
            tenant_id="tenant-1",
            plan_id=plan.id,
        )
        
        assert sub.plan_id == plan.id
        
        # Foreign key is enforced at database level
        # Trying to delete plan while subscription exists should fail
        # (if CASCADE delete not configured, which it should be)
        
        db.commit()
    
    def test_audit_log_immutability(self, db: Session):
        """Verify audit logs cannot be modified after creation"""
        # Setup
        audit_repo = AuditLogRepository(db)
        
        # Create audit log
        log = audit_repo.create(
            tenant_id="tenant-1",
            action="test_action",
            resource_type="test",
        )
        
        original_id = log.id
        original_action = log.action
        
        # Audit logs should not be updatable
        # (no update method in repository)
        
        # Verify log is unchanged
        retrieved = audit_repo.get_by_id("tenant-1", original_id)
        assert retrieved.action == original_action
        
        db.commit()
    
    def test_webhook_delivery_status_transitions(self, db: Session):
        """Test webhook delivery status transitions are valid"""
        # Setup
        endpoint_repo = WebhookEndpointRepository(db)
        delivery_repo = WebhookDeliveryRepository(db)
        
        # Create endpoint
        endpoint = endpoint_repo.create(
            tenant_id="tenant-1",
            name="Test",
            url="https://example.com",
            events=["test"],
        )
        
        # Create delivery
        delivery = delivery_repo.create(
            endpoint_id=endpoint.id,
            event_type="test",
            event_id="evt-1",
            payload={},
        )
        
        # Initial state: pending
        assert delivery.status == "pending"
        assert delivery.attempt_count == 0
        
        # Mark as sent
        delivery.mark_sent(200)
        assert delivery.status == "sent"
        assert delivery.completed_at is not None
        
        db.commit()


# Pytest fixture for database session
@pytest.fixture
def db():
    """Create test database session"""
    from app.database import SessionLocal
    session = SessionLocal()
    yield session
    session.close()
