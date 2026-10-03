from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple
from sqlalchemy.orm import Session
from app.models.subscription import Subscription, SubscriptionStatus, BillingCycle
from app.models.plan import Plan
from app.models.invoice import Invoice, InvoiceStatus
from app.repositories.subscription import SubscriptionRepository
from app.repositories.plan import PlanRepository
from app.repositories.invoice import InvoiceRepository
from app.repositories.usage_record import UsageRecordRepository
from app.repositories.payment_method import PaymentMethodRepository
from app.core.exceptions import ValidationException, ResourceNotFoundException
from uuid import uuid4


class BillingService:
    """Service for subscription and billing operations"""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.subscription_repo = SubscriptionRepository(db_session)
        self.plan_repo = PlanRepository(db_session)
        self.invoice_repo = InvoiceRepository(db_session)
        self.usage_repo = UsageRecordRepository(db_session)
        self.payment_repo = PaymentMethodRepository(db_session)
    
    def create_subscription(
        self,
        tenant_id: str,
        plan_id: str,
        billing_cycle: BillingCycle = BillingCycle.MONTHLY,
        stripe_customer_id: Optional[str] = None,
        stripe_subscription_id: Optional[str] = None,
        payment_method_id: Optional[str] = None,
        trial_days: int = 14
    ) -> Subscription:
        """Create a new subscription for a tenant"""
        
        # Check for existing active subscription
        existing = self.subscription_repo.get_any_active_subscription(tenant_id)
        if existing:
            raise ValidationException("Tenant already has an active subscription")
        
        # Get the plan
        plan = self.plan_repo.get_by_id(plan_id)
        
        # Calculate subscription period
        now = datetime.utcnow()
        trial_end = now + timedelta(days=trial_days) if trial_days > 0 else None
        
        if trial_days > 0:
            period_start = trial_end
            status = SubscriptionStatus.TRIAL
        else:
            period_start = now
            status = SubscriptionStatus.ACTIVE
        
        # Calculate period end based on billing cycle
        if billing_cycle == BillingCycle.MONTHLY:
            period_end = period_start + timedelta(days=30)
            monthly_price = plan.monthly_price
            annual_price = 0
        else:  # ANNUAL
            period_end = period_start + timedelta(days=365)
            monthly_price = 0
            annual_price = plan.annual_price
        
        subscription_data = {
            "tenant_id": tenant_id,
            "plan_id": plan_id,
            "status": status,
            "billing_cycle": billing_cycle,
            "current_period_start": period_start,
            "current_period_end": period_end,
            "trial_start": now if trial_days > 0 else None,
            "trial_end": trial_end,
            "monthly_price": monthly_price,
            "annual_price": annual_price,
            "stripe_customer_id": stripe_customer_id,
            "stripe_subscription_id": stripe_subscription_id,
            "payment_method_id": payment_method_id,
            "auto_renew": True,
        }
        
        subscription = self.subscription_repo.create(subscription_data)
        self.db_session.commit()
        return subscription
    
    def upgrade_subscription(
        self,
        subscription_id: str,
        tenant_id: str,
        new_plan_id: str,
        proration_credits: Optional[float] = None
    ) -> Tuple[Subscription, Optional[Invoice]]:
        """Upgrade a subscription to a higher tier plan"""
        
        subscription = self.subscription_repo.get_by_id(subscription_id, tenant_id)
        old_plan = self.plan_repo.get_by_id(subscription.plan_id)
        new_plan = self.plan_repo.get_by_id(new_plan_id)
        
        # Validate upgrade direction (basic check)
        plan_order = {"free": 0, "starter": 1, "professional": 2, "enterprise": 3}
        if plan_order.get(old_plan.slug, 0) >= plan_order.get(new_plan.slug, 0):
            raise ValidationException("Can only upgrade to a higher tier plan")
        
        # Calculate prorated amount
        days_remaining = subscription.days_until_renewal()
        if days_remaining > 0 and subscription.billing_cycle == BillingCycle.MONTHLY:
            daily_rate_old = subscription.monthly_price / 30
            daily_rate_new = new_plan.monthly_price / 30
            proration_credits = (daily_rate_new - daily_rate_old) * days_remaining
        
        # Update subscription
        update_data = {
            "plan_id": new_plan_id,
            "monthly_price": new_plan.monthly_price,
            "annual_price": new_plan.annual_price,
        }
        subscription = self.subscription_repo.update(subscription_id, tenant_id, update_data)
        
        # Create invoice if there's a charge
        invoice = None
        if proration_credits and proration_credits > 0:
            invoice_data = {
                "tenant_id": tenant_id,
                "subscription_id": subscription_id,
                "invoice_number": self._generate_invoice_number(tenant_id),
                "status": InvoiceStatus.SENT,
                "issue_date": datetime.utcnow(),
                "due_date": datetime.utcnow() + timedelta(days=7),
                "subtotal": proration_credits,
                "tax_amount": 0,
                "discount_amount": 0,
                "total_amount": proration_credits,
                "description": f"Upgrade from {old_plan.name} to {new_plan.name}",
            }
            invoice = self.invoice_repo.create(invoice_data)
        
        self.db_session.commit()
        return subscription, invoice
    
    def downgrade_subscription(
        self,
        subscription_id: str,
        tenant_id: str,
        new_plan_id: str
    ) -> Subscription:
        """Downgrade a subscription to a lower tier plan (effective next period)"""
        
        subscription = self.subscription_repo.get_by_id(subscription_id, tenant_id)
        new_plan = self.plan_repo.get_by_id(new_plan_id)
        
        # Downgrades take effect at next renewal
        update_data = {
            "plan_id": new_plan_id,
            "monthly_price": new_plan.monthly_price,
            "annual_price": new_plan.annual_price,
        }
        subscription = self.subscription_repo.update(subscription_id, tenant_id, update_data)
        
        self.db_session.commit()
        return subscription
    
    def cancel_subscription(
        self,
        subscription_id: str,
        tenant_id: str,
        reason: str = None,
        effective_immediately: bool = False
    ) -> Subscription:
        """Cancel a subscription"""
        
        subscription = self.subscription_repo.cancel(subscription_id, tenant_id, reason)
        
        if effective_immediately:
            subscription.current_period_end = datetime.utcnow()
        
        self.db_session.commit()
        return subscription
    
    def renew_subscription(self, subscription_id: str, tenant_id: str) -> Invoice:
        """Renew a subscription and create invoice for next period"""
        
        subscription = self.subscription_repo.get_by_id(subscription_id, tenant_id)
        
        if subscription.status not in [SubscriptionStatus.ACTIVE, SubscriptionStatus.PAST_DUE]:
            raise ValidationException("Only active subscriptions can be renewed")
        
        # Create new invoice for renewal
        amount = subscription.monthly_price if subscription.billing_cycle == BillingCycle.MONTHLY else subscription.annual_price
        
        invoice_data = {
            "tenant_id": tenant_id,
            "subscription_id": subscription_id,
            "invoice_number": self._generate_invoice_number(tenant_id),
            "status": InvoiceStatus.SENT,
            "issue_date": datetime.utcnow(),
            "due_date": datetime.utcnow() + timedelta(days=7),
            "subtotal": amount,
            "tax_amount": 0,
            "discount_amount": 0,
            "total_amount": amount,
            "description": f"{subscription.billing_cycle.value.capitalize()} subscription renewal",
        }
        invoice = self.invoice_repo.create(invoice_data)
        
        # Update subscription period
        days_offset = 30 if subscription.billing_cycle == BillingCycle.MONTHLY else 365
        subscription.current_period_start = subscription.current_period_end
        subscription.current_period_end = subscription.current_period_end + timedelta(days=days_offset)
        
        self.db_session.commit()
        return invoice
    
    def _generate_invoice_number(self, tenant_id: str) -> str:
        """Generate unique invoice number"""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"INV-{tenant_id[:8].upper()}-{timestamp}"
    
    def get_billing_overview(self, tenant_id: str) -> Dict:
        """Get billing overview for a tenant"""
        
        subscription = self.subscription_repo.get_any_active_subscription(tenant_id)
        if not subscription:
            return {"status": "no_subscription"}
        
        plan = self.plan_repo.get_by_id(subscription.plan_id)
        payment_method = None
        if subscription.payment_method_id:
            try:
                payment_method = self.payment_repo.get_by_id(subscription.payment_method_id, tenant_id)
            except ResourceNotFoundException:
                pass
        
        recent_invoices = self.invoice_repo.list_by_subscription(subscription.id, tenant_id)[:5]
        
        return {
            "subscription": {
                "id": str(subscription.id),
                "status": subscription.status.value,
                "plan_name": plan.name,
                "billing_cycle": subscription.billing_cycle.value,
                "current_period_start": subscription.current_period_start.isoformat(),
                "current_period_end": subscription.current_period_end.isoformat(),
                "days_until_renewal": subscription.days_until_renewal(),
                "auto_renew": subscription.auto_renew,
            },
            "pricing": {
                "monthly_price": subscription.monthly_price,
                "annual_price": subscription.annual_price,
            },
            "payment_method": {
                "id": str(payment_method.id) if payment_method else None,
                "display_name": payment_method.display_name() if payment_method else None,
                "is_valid": payment_method.is_valid if payment_method else None,
            } if payment_method else None,
            "recent_invoices": [
                {
                    "id": str(inv.id),
                    "invoice_number": inv.invoice_number,
                    "status": inv.status.value,
                    "amount": inv.total_amount,
                    "issue_date": inv.issue_date.isoformat(),
                }
                for inv in recent_invoices
            ],
        }
