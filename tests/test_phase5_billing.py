"""Phase 5 Billing & Subscriptions Test Suite"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.plan import Plan, PlanTier
from app.models.subscription import Subscription, SubscriptionStatus, BillingCycle
from app.models.invoice import Invoice, InvoiceStatus
from app.models.usage_record import UsageRecord
from app.models.payment_method import PaymentMethod
from app.repositories.plan import PlanRepository
from app.repositories.subscription import SubscriptionRepository
from app.repositories.invoice import InvoiceRepository
from app.repositories.usage_record import UsageRecordRepository
from app.repositories.payment_method import PaymentMethodRepository
from app.services.billing import BillingService
from app.services.invoice import InvoiceService
from app.services.usage import UsageService
from app.core.exceptions import NotFoundError, ValidationError


class TestPlanRepository:
    """Tests for PlanRepository"""
    
    def test_create_plan(self, db_session: Session):
        """Test creating a plan"""
        plan_data = {
            "name": "Professional",
            "slug": "professional",
            "tier": PlanTier.PROFESSIONAL,
            "description": "Professional plan",
            "monthly_price": 99.0,
            "annual_price": 999.0,
            "max_users": 50,
            "max_applications": 10,
            "api_requests_per_month": 100000,
        }
        
        repo = PlanRepository(db_session)
        plan = repo.create(plan_data)
        
        assert plan.name == "Professional"
        assert plan.tier == PlanTier.PROFESSIONAL
        assert plan.monthly_price == 99.0
        assert plan.is_active is True
    
    def test_get_plan_by_id(self, db_session: Session):
        """Test retrieving a plan by ID"""
        plan_data = {
            "name": "Starter",
            "slug": "starter",
            "tier": PlanTier.STARTER,
            "monthly_price": 29.0,
            "annual_price": 290.0,
        }
        
        repo = PlanRepository(db_session)
        created_plan = repo.create(plan_data)
        db_session.commit()
        
        retrieved_plan = repo.get_by_id(str(created_plan.id))
        assert retrieved_plan.id == created_plan.id
        assert retrieved_plan.name == "Starter"
    
    def test_get_plan_by_slug(self, db_session: Session):
        """Test retrieving a plan by slug"""
        plan_data = {
            "name": "Free",
            "slug": "free",
            "tier": PlanTier.FREE,
            "monthly_price": 0.0,
            "annual_price": 0.0,
            "is_default": True,
        }
        
        repo = PlanRepository(db_session)
        created_plan = repo.create(plan_data)
        db_session.commit()
        
        retrieved_plan = repo.get_by_slug("free")
        assert retrieved_plan.slug == "free"
    
    def test_list_active_plans(self, db_session: Session):
        """Test listing active plans"""
        plan_data_1 = {
            "name": "Plan 1",
            "slug": "plan-1",
            "tier": PlanTier.STARTER,
            "monthly_price": 29.0,
            "annual_price": 290.0,
            "is_active": True,
            "display_order": 1,
        }
        plan_data_2 = {
            "name": "Plan 2",
            "slug": "plan-2",
            "tier": PlanTier.PROFESSIONAL,
            "monthly_price": 99.0,
            "annual_price": 999.0,
            "is_active": True,
            "display_order": 2,
        }
        
        repo = PlanRepository(db_session)
        repo.create(plan_data_1)
        repo.create(plan_data_2)
        db_session.commit()
        
        plans = repo.list()
        assert len(plans) >= 2
    
    def test_get_default_plan(self, db_session: Session):
        """Test getting the default plan"""
        plan_data = {
            "name": "Free Tier",
            "slug": "free-tier",
            "tier": PlanTier.FREE,
            "monthly_price": 0.0,
            "annual_price": 0.0,
            "is_default": True,
        }
        
        repo = PlanRepository(db_session)
        created_plan = repo.create(plan_data)
        db_session.commit()
        
        default_plan = repo.get_default_plan()
        assert default_plan.is_default is True
    
    def test_update_plan(self, db_session: Session):
        """Test updating a plan"""
        plan_data = {
            "name": "Original",
            "slug": "original",
            "tier": PlanTier.STARTER,
            "monthly_price": 29.0,
            "annual_price": 290.0,
        }
        
        repo = PlanRepository(db_session)
        plan = repo.create(plan_data)
        db_session.commit()
        
        updated_data = {"monthly_price": 39.0}
        updated_plan = repo.update(str(plan.id), updated_data)
        
        assert updated_plan.monthly_price == 39.0


class TestSubscriptionRepository:
    """Tests for SubscriptionRepository"""
    
    def _create_plan(self, db_session: Session, name: str = "Test Plan"):
        """Helper to create a plan"""
        plan_data = {
            "name": name,
            "slug": name.lower().replace(" ", "-"),
            "tier": PlanTier.PROFESSIONAL,
            "monthly_price": 99.0,
            "annual_price": 999.0,
        }
        plan = Plan(**plan_data)
        db_session.add(plan)
        db_session.flush()
        return plan
    
    def test_create_subscription(self, db_session: Session, test_tenant):
        """Test creating a subscription"""
        plan = self._create_plan(db_session)
        
        sub_data = {
            "tenant_id": str(test_tenant.id),
            "plan_id": str(plan.id),
            "status": SubscriptionStatus.ACTIVE,
            "billing_cycle": BillingCycle.MONTHLY,
            "current_period_start": datetime.utcnow(),
            "current_period_end": datetime.utcnow() + timedelta(days=30),
            "monthly_price": 99.0,
        }
        
        repo = SubscriptionRepository(db_session)
        subscription = repo.create(sub_data)
        
        assert subscription.status == SubscriptionStatus.ACTIVE
        assert subscription.billing_cycle == BillingCycle.MONTHLY
    
    def test_get_active_subscription(self, db_session: Session, test_tenant):
        """Test getting active subscription"""
        plan = self._create_plan(db_session)
        
        sub_data = {
            "tenant_id": str(test_tenant.id),
            "plan_id": str(plan.id),
            "status": SubscriptionStatus.ACTIVE,
            "billing_cycle": BillingCycle.MONTHLY,
            "current_period_start": datetime.utcnow(),
            "current_period_end": datetime.utcnow() + timedelta(days=30),
        }
        
        repo = SubscriptionRepository(db_session)
        created_sub = repo.create(sub_data)
        db_session.commit()
        
        retrieved_sub = repo.get_active_subscription(str(test_tenant.id))
        assert retrieved_sub.id == created_sub.id
    
    def test_get_trial_subscription(self, db_session: Session, test_tenant):
        """Test getting trial subscription"""
        plan = self._create_plan(db_session)
        
        sub_data = {
            "tenant_id": str(test_tenant.id),
            "plan_id": str(plan.id),
            "status": SubscriptionStatus.TRIAL,
            "billing_cycle": BillingCycle.MONTHLY,
            "current_period_start": datetime.utcnow(),
            "current_period_end": datetime.utcnow() + timedelta(days=30),
            "trial_start": datetime.utcnow(),
            "trial_end": datetime.utcnow() + timedelta(days=14),
        }
        
        repo = SubscriptionRepository(db_session)
        created_sub = repo.create(sub_data)
        db_session.commit()
        
        retrieved_sub = repo.get_trial_subscription(str(test_tenant.id))
        assert retrieved_sub.status == SubscriptionStatus.TRIAL
    
    def test_cancel_subscription(self, db_session: Session, test_tenant):
        """Test cancelling a subscription"""
        plan = self._create_plan(db_session)
        
        sub_data = {
            "tenant_id": str(test_tenant.id),
            "plan_id": str(plan.id),
            "status": SubscriptionStatus.ACTIVE,
            "billing_cycle": BillingCycle.MONTHLY,
            "current_period_start": datetime.utcnow(),
            "current_period_end": datetime.utcnow() + timedelta(days=30),
        }
        
        repo = SubscriptionRepository(db_session)
        subscription = repo.create(sub_data)
        db_session.commit()
        
        cancelled = repo.cancel(str(subscription.id), str(test_tenant.id), reason="User requested")
        assert cancelled.status == SubscriptionStatus.CANCELLED
        assert cancelled.cancellation_reason == "User requested"


class TestInvoiceRepository:
    """Tests for InvoiceRepository"""
    
    def _create_subscription(self, db_session: Session, test_tenant):
        """Helper to create a subscription"""
        plan_data = {
            "name": "Invoice Test Plan",
            "slug": "invoice-test-plan",
            "tier": PlanTier.PROFESSIONAL,
            "monthly_price": 99.0,
            "annual_price": 999.0,
        }
        plan = Plan(**plan_data)
        db_session.add(plan)
        db_session.flush()
        
        sub_data = {
            "tenant_id": str(test_tenant.id),
            "plan_id": str(plan.id),
            "status": SubscriptionStatus.ACTIVE,
            "billing_cycle": BillingCycle.MONTHLY,
            "current_period_start": datetime.utcnow(),
            "current_period_end": datetime.utcnow() + timedelta(days=30),
        }
        
        subscription = Subscription(**sub_data)
        db_session.add(subscription)
        db_session.flush()
        return subscription
    
    def test_create_invoice(self, db_session: Session, test_tenant):
        """Test creating an invoice"""
        subscription = self._create_subscription(db_session, test_tenant)
        
        invoice_data = {
            "tenant_id": str(test_tenant.id),
            "subscription_id": str(subscription.id),
            "invoice_number": "INV-001",
            "status": InvoiceStatus.SENT,
            "issue_date": datetime.utcnow(),
            "due_date": datetime.utcnow() + timedelta(days=7),
            "subtotal": 99.0,
            "tax_amount": 0,
            "total_amount": 99.0,
        }
        
        repo = InvoiceRepository(db_session)
        invoice = repo.create(invoice_data)
        
        assert invoice.invoice_number == "INV-001"
        assert invoice.status == InvoiceStatus.SENT
    
    def test_mark_paid(self, db_session: Session, test_tenant):
        """Test marking invoice as paid"""
        subscription = self._create_subscription(db_session, test_tenant)
        
        invoice_data = {
            "tenant_id": str(test_tenant.id),
            "subscription_id": str(subscription.id),
            "invoice_number": "INV-002",
            "status": InvoiceStatus.PENDING,
            "issue_date": datetime.utcnow(),
            "due_date": datetime.utcnow() + timedelta(days=7),
            "subtotal": 99.0,
            "tax_amount": 0,
            "total_amount": 99.0,
        }
        
        repo = InvoiceRepository(db_session)
        invoice = repo.create(invoice_data)
        db_session.commit()
        
        paid_invoice = repo.mark_paid(str(invoice.id), str(test_tenant.id), 99.0)
        assert paid_invoice.status == InvoiceStatus.PAID
        assert paid_invoice.paid_amount == 99.0
    
    def test_list_overdue_invoices(self, db_session: Session, test_tenant):
        """Test listing overdue invoices"""
        subscription = self._create_subscription(db_session, test_tenant)
        
        invoice_data = {
            "tenant_id": str(test_tenant.id),
            "subscription_id": str(subscription.id),
            "invoice_number": "INV-003",
            "status": InvoiceStatus.OVERDUE,
            "issue_date": datetime.utcnow() - timedelta(days=10),
            "due_date": datetime.utcnow() - timedelta(days=3),
            "subtotal": 99.0,
            "tax_amount": 0,
            "total_amount": 99.0,
        }
        
        repo = InvoiceRepository(db_session)
        repo.create(invoice_data)
        db_session.commit()
        
        overdue = repo.list_overdue()
        assert len(overdue) > 0


class TestUsageRecordRepository:
    """Tests for UsageRecordRepository"""
    
    def _create_subscription(self, db_session: Session, test_tenant):
        """Helper to create a subscription"""
        plan_data = {
            "name": "Usage Test Plan",
            "slug": "usage-test-plan",
            "tier": PlanTier.PROFESSIONAL,
            "monthly_price": 99.0,
        }
        plan = Plan(**plan_data)
        db_session.add(plan)
        db_session.flush()
        
        sub_data = {
            "tenant_id": str(test_tenant.id),
            "plan_id": str(plan.id),
            "status": SubscriptionStatus.ACTIVE,
            "billing_cycle": BillingCycle.MONTHLY,
            "current_period_start": datetime.utcnow(),
            "current_period_end": datetime.utcnow() + timedelta(days=30),
        }
        
        subscription = Subscription(**sub_data)
        db_session.add(subscription)
        db_session.flush()
        return subscription
    
    def test_track_usage(self, db_session: Session, test_tenant):
        """Test tracking usage"""
        subscription = self._create_subscription(db_session, test_tenant)
        
        repo = UsageRecordRepository(db_session)
        record = repo.create({
            "tenant_id": str(test_tenant.id),
            "subscription_id": str(subscription.id),
            "metric_name": "api_calls",
            "metric_value": 1000,
            "billing_period_start": datetime.utcnow(),
            "billing_period_end": datetime.utcnow() + timedelta(days=30),
        })
        
        assert record.metric_name == "api_calls"
        assert record.metric_value == 1000
    
    def test_increment_usage(self, db_session: Session, test_tenant):
        """Test incrementing usage"""
        subscription = self._create_subscription(db_session, test_tenant)
        period_start = datetime.utcnow()
        period_end = period_start + timedelta(days=30)
        
        repo = UsageRecordRepository(db_session)
        
        # Create initial record
        record1 = repo.increment_usage(
            str(test_tenant.id),
            "api_calls",
            500,
            period_start,
            period_end
        )
        db_session.commit()
        
        # Increment
        record2 = repo.increment_usage(
            str(test_tenant.id),
            "api_calls",
            500,
            period_start,
            period_end
        )
        
        assert record2.metric_value == 1000


class TestPaymentMethodRepository:
    """Tests for PaymentMethodRepository"""
    
    def test_create_payment_method(self, db_session: Session, test_tenant):
        """Test creating a payment method"""
        pm_data = {
            "tenant_id": str(test_tenant.id),
            "stripe_payment_method_id": "pm_test_123",
            "stripe_customer_id": "cus_test_123",
            "payment_type": "card",
            "card_brand": "visa",
            "card_last_4": "4242",
        }
        
        repo = PaymentMethodRepository(db_session)
        method = repo.create(pm_data)
        
        assert method.payment_type == "card"
        assert method.is_default is True  # First method should be default
    
    def test_get_default_method(self, db_session: Session, test_tenant):
        """Test getting default payment method"""
        pm_data = {
            "tenant_id": str(test_tenant.id),
            "stripe_payment_method_id": "pm_test_456",
            "stripe_customer_id": "cus_test_456",
            "payment_type": "card",
            "card_last_4": "4242",
            "is_default": True,
        }
        
        repo = PaymentMethodRepository(db_session)
        created = repo.create(pm_data)
        db_session.commit()
        
        default = repo.get_default_method(str(test_tenant.id))
        assert default.id == created.id
    
    def test_set_as_default(self, db_session: Session, test_tenant):
        """Test setting a payment method as default"""
        pm_data_1 = {
            "tenant_id": str(test_tenant.id),
            "stripe_payment_method_id": "pm_test_1",
            "stripe_customer_id": "cus_test_1",
            "payment_type": "card",
        }
        pm_data_2 = {
            "tenant_id": str(test_tenant.id),
            "stripe_payment_method_id": "pm_test_2",
            "stripe_customer_id": "cus_test_1",
            "payment_type": "card",
            "is_default": False,
        }
        
        repo = PaymentMethodRepository(db_session)
        method1 = repo.create(pm_data_1)
        method2 = repo.create(pm_data_2)
        db_session.commit()
        
        repo.set_as_default(str(method2.id), str(test_tenant.id))
        db_session.commit()
        
        default = repo.get_default_method(str(test_tenant.id))
        assert default.id == method2.id


class TestBillingService:
    """Tests for BillingService"""
    
    def _create_plan(self, db_session: Session, name: str = "Test", tier: PlanTier = PlanTier.PROFESSIONAL):
        """Helper to create a plan"""
        plan_data = {
            "name": name,
            "slug": name.lower().replace(" ", "-"),
            "tier": tier,
            "monthly_price": 99.0 if tier != PlanTier.FREE else 0.0,
            "annual_price": 999.0 if tier != PlanTier.FREE else 0.0,
        }
        plan = Plan(**plan_data)
        db_session.add(plan)
        db_session.flush()
        return plan
    
    def test_create_subscription(self, db_session: Session, test_tenant):
        """Test creating a subscription"""
        plan = self._create_plan(db_session)
        
        service = BillingService(db_session)
        subscription = service.create_subscription(
            tenant_id=str(test_tenant.id),
            plan_id=str(plan.id),
            billing_cycle=BillingCycle.MONTHLY,
            trial_days=14
        )
        
        assert subscription.status == SubscriptionStatus.TRIAL
        assert subscription.tenant_id == test_tenant.id
    
    def test_upgrade_subscription(self, db_session: Session, test_tenant):
        """Test upgrading a subscription"""
        plan1 = self._create_plan(db_session, "Starter", PlanTier.STARTER)
        plan2 = self._create_plan(db_session, "Professional", PlanTier.PROFESSIONAL)
        
        service = BillingService(db_session)
        
        # Create initial subscription
        subscription = service.create_subscription(
            str(test_tenant.id),
            str(plan1.id),
            trial_days=0
        )
        
        # Upgrade
        upgraded, invoice = service.upgrade_subscription(
            str(subscription.id),
            str(test_tenant.id),
            str(plan2.id)
        )
        
        assert upgraded.plan_id == plan2.id
    
    def test_cancel_subscription(self, db_session: Session, test_tenant):
        """Test cancelling a subscription"""
        plan = self._create_plan(db_session)
        
        service = BillingService(db_session)
        subscription = service.create_subscription(
            str(test_tenant.id),
            str(plan.id),
            trial_days=0
        )
        
        cancelled = service.cancel_subscription(
            str(subscription.id),
            str(test_tenant.id),
            reason="User requested"
        )
        
        assert cancelled.status == SubscriptionStatus.CANCELLED
        assert cancelled.cancellation_reason == "User requested"


class TestInvoiceService:
    """Tests for InvoiceService"""
    
    def _create_subscription(self, db_session: Session, test_tenant):
        """Helper to create a subscription"""
        plan_data = {
            "name": "Invoice Service Plan",
            "slug": "invoice-service-plan",
            "tier": PlanTier.PROFESSIONAL,
            "monthly_price": 99.0,
        }
        plan = Plan(**plan_data)
        db_session.add(plan)
        db_session.flush()
        
        sub_data = {
            "tenant_id": str(test_tenant.id),
            "plan_id": str(plan.id),
            "status": SubscriptionStatus.ACTIVE,
            "billing_cycle": BillingCycle.MONTHLY,
            "current_period_start": datetime.utcnow(),
            "current_period_end": datetime.utcnow() + timedelta(days=30),
        }
        
        subscription = Subscription(**sub_data)
        db_session.add(subscription)
        db_session.flush()
        return subscription
    
    def test_record_payment(self, db_session: Session, test_tenant):
        """Test recording a payment"""
        subscription = self._create_subscription(db_session, test_tenant)
        
        invoice_data = {
            "tenant_id": str(test_tenant.id),
            "subscription_id": str(subscription.id),
            "invoice_number": "INV-PAY-001",
            "status": InvoiceStatus.PENDING,
            "issue_date": datetime.utcnow(),
            "due_date": datetime.utcnow() + timedelta(days=7),
            "subtotal": 99.0,
            "tax_amount": 0,
            "total_amount": 99.0,
        }
        
        invoice = Invoice(**invoice_data)
        db_session.add(invoice)
        db_session.commit()
        
        service = InvoiceService(db_session)
        paid = service.record_payment(
            str(invoice.id),
            str(test_tenant.id),
            99.0
        )
        
        assert paid.status == InvoiceStatus.PAID


class TestUsageService:
    """Tests for UsageService"""
    
    def _create_subscription(self, db_session: Session, test_tenant):
        """Helper to create a subscription"""
        plan_data = {
            "name": "Usage Service Plan",
            "slug": "usage-service-plan",
            "tier": PlanTier.PROFESSIONAL,
            "monthly_price": 99.0,
            "api_requests_per_month": 100000,
        }
        plan = Plan(**plan_data)
        db_session.add(plan)
        db_session.flush()
        
        sub_data = {
            "tenant_id": str(test_tenant.id),
            "plan_id": str(plan.id),
            "status": SubscriptionStatus.ACTIVE,
            "billing_cycle": BillingCycle.MONTHLY,
            "current_period_start": datetime.utcnow(),
            "current_period_end": datetime.utcnow() + timedelta(days=30),
        }
        
        subscription = Subscription(**sub_data)
        db_session.add(subscription)
        db_session.flush()
        return subscription
    
    def test_track_usage(self, db_session: Session, test_tenant):
        """Test tracking usage"""
        self._create_subscription(db_session, test_tenant)
        
        service = UsageService(db_session)
        record = service.track_usage(
            str(test_tenant.id),
            "api_calls",
            500
        )
        
        assert record.metric_name == "api_calls"
        assert record.metric_value == 500
    
    def test_check_usage_limits(self, db_session: Session, test_tenant):
        """Test checking usage limits"""
        self._create_subscription(db_session, test_tenant)
        
        service = UsageService(db_session)
        
        # Track usage
        service.track_usage(str(test_tenant.id), "api_calls", 50000)
        db_session.commit()
        
        # Check limits
        limits = service.check_usage_limits(str(test_tenant.id))
        assert "exceeded_limits" in limits
    
    def test_get_current_usage(self, db_session: Session, test_tenant):
        """Test getting current usage"""
        self._create_subscription(db_session, test_tenant)
        
        service = UsageService(db_session)
        service.track_usage(str(test_tenant.id), "api_calls", 1000)
        db_session.commit()
        
        usage = service.get_current_usage(str(test_tenant.id))
        assert "metrics" in usage
        assert "api_calls" in usage["metrics"]
