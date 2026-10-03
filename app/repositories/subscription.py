from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import datetime
from app.models.subscription import Subscription, SubscriptionStatus, BillingCycle
from app.core.exceptions import ResourceNotFoundException, ValidationException


class SubscriptionRepository:
    """Repository for Subscription operations"""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
    
    def get_by_id(self, subscription_id: str, tenant_id: str) -> Subscription:
        """Get subscription by ID (tenant-scoped)"""
        subscription = self.db_session.query(Subscription).filter_by(
            id=subscription_id,
            tenant_id=tenant_id
        ).first()
        if not subscription:
            raise ResourceNotFoundException(f"Subscription {subscription_id} not found")
        return subscription
    
    def get_active_subscription(self, tenant_id: str) -> Optional[Subscription]:
        """Get active subscription for tenant"""
        return self.db_session.query(Subscription).filter_by(
            tenant_id=tenant_id,
            status=SubscriptionStatus.ACTIVE
        ).first()
    
    def get_trial_subscription(self, tenant_id: str) -> Optional[Subscription]:
        """Get trial subscription for tenant"""
        return self.db_session.query(Subscription).filter_by(
            tenant_id=tenant_id,
            status=SubscriptionStatus.TRIAL
        ).first()
    
    def get_any_active_subscription(self, tenant_id: str) -> Optional[Subscription]:
        """Get any active subscription (active or trial)"""
        return self.db_session.query(Subscription).filter(
            Subscription.tenant_id == tenant_id,
            Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL])
        ).first()
    
    def get_by_stripe_subscription_id(self, stripe_subscription_id: str) -> Optional[Subscription]:
        """Get subscription by Stripe ID"""
        return self.db_session.query(Subscription).filter_by(
            stripe_subscription_id=stripe_subscription_id
        ).first()
    
    def list_by_tenant(self, tenant_id: str) -> List[Subscription]:
        """List all subscriptions for tenant"""
        return self.db_session.query(Subscription).filter_by(
            tenant_id=tenant_id
        ).order_by(Subscription.created_at.desc()).all()
    
    def list_expiring_soon(self, days: int = 7) -> List[Subscription]:
        """List subscriptions expiring within N days"""
        from datetime import timedelta
        cutoff_date = datetime.utcnow() + timedelta(days=days)
        return self.db_session.query(Subscription).filter(
            Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL]),
            Subscription.current_period_end <= cutoff_date
        ).all()
    
    def list_overdue(self) -> List[Subscription]:
        """List subscriptions with overdue payments"""
        return self.db_session.query(Subscription).filter(
            Subscription.status == SubscriptionStatus.PAST_DUE
        ).all()
    
    def create(self, subscription_data: dict) -> Subscription:
        """Create a new subscription"""
        subscription = Subscription(**subscription_data)
        self.db_session.add(subscription)
        self.db_session.flush()
        return subscription
    
    def update(self, subscription_id: str, tenant_id: str, subscription_data: dict) -> Subscription:
        """Update an existing subscription"""
        subscription = self.get_by_id(subscription_id, tenant_id)
        for key, value in subscription_data.items():
            setattr(subscription, key, value)
        self.db_session.flush()
        return subscription
    
    def cancel(self, subscription_id: str, tenant_id: str, reason: str = None) -> Subscription:
        """Cancel a subscription"""
        subscription = self.get_by_id(subscription_id, tenant_id)
        subscription.status = SubscriptionStatus.CANCELLED
        subscription.cancelled_at = datetime.utcnow()
        subscription.cancellation_reason = reason
        self.db_session.flush()
        return subscription
    
    def pause(self, subscription_id: str, tenant_id: str) -> Subscription:
        """Pause a subscription"""
        subscription = self.get_by_id(subscription_id, tenant_id)
        subscription.status = SubscriptionStatus.PAUSED
        self.db_session.flush()
        return subscription
    
    def resume(self, subscription_id: str, tenant_id: str) -> Subscription:
        """Resume a paused subscription"""
        subscription = self.get_by_id(subscription_id, tenant_id)
        if subscription.status != SubscriptionStatus.PAUSED:
            raise ValidationException("Only paused subscriptions can be resumed")
        subscription.status = SubscriptionStatus.ACTIVE
        self.db_session.flush()
        return subscription
