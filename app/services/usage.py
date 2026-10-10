from datetime import datetime, timedelta
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from app.models.usage_record import UsageRecord
from app.models.subscription import Subscription
from app.repositories.usage_record import UsageRecordRepository
from app.repositories.subscription import SubscriptionRepository
from app.repositories.plan import PlanRepository
from app.core.exceptions import ValidationException, ResourceNotFoundException


class UsageService:
    """Service for tracking and metering resource usage"""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.usage_repo = UsageRecordRepository(db_session)
        self.subscription_repo = SubscriptionRepository(db_session)
        self.plan_repo = PlanRepository(db_session)
    
    # Common metric names
    METRIC_API_CALLS = "api_calls"
    METRIC_STORAGE_GB = "storage_gb"
    METRIC_USERS = "users"
    METRIC_APPLICATIONS = "applications"
    METRIC_API_KEYS = "api_keys"
    
    def track_usage(
        self,
        tenant_id: str,
        metric_name: str,
        amount: float,
        description: str = None
    ) -> UsageRecord:
        """Track resource usage"""
        
        # Get active subscription
        subscription = self.subscription_repo.get_any_active_subscription(tenant_id)
        if not subscription:
            raise ValidationException("Tenant has no active subscription")
        
        # Get current billing period
        period_start = subscription.current_period_start
        period_end = subscription.current_period_end
        
        # Increment usage
        usage = self.usage_repo.increment_usage(
            tenant_id=tenant_id,
            subscription_id=str(subscription.id),
            metric_name=metric_name,
            amount=amount,
            period_start=period_start,
            period_end=period_end
        )
        
        # Update subscription if tracking this metric
        if metric_name == self.METRIC_API_CALLS:
            subscription.current_api_calls = int(subscription.current_api_calls + amount)
        elif metric_name == self.METRIC_STORAGE_GB:
            subscription.current_usage_gb += amount
        elif metric_name == self.METRIC_USERS:
            subscription.current_user_count = int(subscription.current_user_count + amount)
        
        self.db_session.commit()
        return usage
    
    def get_current_usage(self, tenant_id: str) -> Dict:
        """Get current usage metrics for a tenant"""
        
        subscription = self.subscription_repo.get_any_active_subscription(tenant_id)
        if not subscription:
            return {
                "subscription_id": None,
                "plan_name": None,
                "current_period_start": None,
                "current_period_end": None,
                "metrics": {},
                "status": "no_subscription",
            }
        
        plan = self.plan_repo.get_by_id(subscription.plan_id)
        
        # Calculate usage percentages
        api_calls_percent = 0
        if plan.api_requests_per_month > 0:
            api_calls_percent = min(100, (subscription.current_api_calls / plan.api_requests_per_month) * 100)
        
        storage_percent = 0
        if plan.storage_gb > 0:
            storage_percent = min(100, (subscription.current_usage_gb / plan.storage_gb) * 100)
        
        users_percent = 0
        if plan.max_users > 0:
            users_percent = min(100, (subscription.current_user_count / plan.max_users) * 100)
        
        return {
            "subscription_id": str(subscription.id),
            "plan_name": plan.name,
            "current_period_start": subscription.current_period_start.isoformat(),
            "current_period_end": subscription.current_period_end.isoformat(),
            "metrics": {
                "api_calls": {
                    "used": subscription.current_api_calls,
                    "limit": plan.api_requests_per_month if plan.api_requests_per_month > 0 else None,
                    "percent": api_calls_percent,
                },
                "storage": {
                    "used": subscription.current_usage_gb,
                    "limit": plan.storage_gb if plan.storage_gb > 0 else None,
                    "percent": storage_percent,
                    "unit": "GB",
                },
                "users": {
                    "used": subscription.current_user_count,
                    "limit": plan.max_users if plan.max_users > 0 else None,
                    "percent": users_percent,
                },
            },
        }
    
    def check_usage_limits(self, tenant_id: str) -> Dict:
        """Check if tenant has exceeded any usage limits"""
        
        subscription = self.subscription_repo.get_any_active_subscription(tenant_id)
        if not subscription:
            return {"status": "no_subscription"}
        
        plan = self.plan_repo.get_by_id(subscription.plan_id)
        
        exceeded = []
        
        # Check API calls limit
        if plan.api_requests_per_month > 0 and subscription.current_api_calls >= plan.api_requests_per_month:
            exceeded.append({
                "metric": self.METRIC_API_CALLS,
                "used": subscription.current_api_calls,
                "limit": plan.api_requests_per_month,
            })
        
        # Check storage limit
        if plan.storage_gb > 0 and subscription.current_usage_gb >= plan.storage_gb:
            exceeded.append({
                "metric": self.METRIC_STORAGE_GB,
                "used": subscription.current_usage_gb,
                "limit": plan.storage_gb,
            })
        
        # Check users limit
        if plan.max_users > 0 and subscription.current_user_count >= plan.max_users:
            exceeded.append({
                "metric": self.METRIC_USERS,
                "used": subscription.current_user_count,
                "limit": plan.max_users,
            })
        
        return {
            "has_exceeded": len(exceeded) > 0,
            "exceeded_limits": exceeded,
        }
    
    def get_usage_history(
        self,
        tenant_id: str,
        metric_name: str,
        days: int = 30
    ) -> List[Dict]:
        """Get usage history for a metric"""
        
        # Get active subscription
        subscription = self.subscription_repo.get_any_active_subscription(tenant_id)
        if not subscription:
            return []
        
        period_start = subscription.current_period_start - timedelta(days=days)
        period_end = subscription.current_period_end
        
        records = self.usage_repo.list_by_metric(
            tenant_id=tenant_id,
            metric_name=metric_name,
            period_start=period_start,
            period_end=period_end
        )
        
        return [
            {
                "id": str(record.id),
                "metric": record.metric_name,
                "value": record.metric_value,
                "billing_period_start": record.billing_period_start.isoformat(),
                "billing_period_end": record.billing_period_end.isoformat(),
                "recorded_at": record.created_at.isoformat(),
            }
            for record in records
        ]
    
    def reset_billing_period(self, tenant_id: str) -> None:
        """Reset usage for a new billing period (called at subscription renewal)"""
        
        subscription = self.subscription_repo.get_any_active_subscription(tenant_id)
        if not subscription:
            return
        
        # Archive old usage records
        old_period_end = subscription.current_period_start
        
        # Reset metrics
        subscription.current_api_calls = 0
        subscription.current_usage_gb = 0.0
        subscription.current_user_count = 0
        
        self.db_session.commit()
    
    def get_usage_report(
        self,
        tenant_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict:
        """Get comprehensive usage report for a period"""
        
        records = self.db_session.query(UsageRecord).filter(
            UsageRecord.tenant_id == tenant_id,
            UsageRecord.created_at >= start_date,
            UsageRecord.created_at <= end_date,
        ).all()
        
        # Group by metric
        metrics = {}
        for record in records:
            if record.metric_name not in metrics:
                metrics[record.metric_name] = []
            metrics[record.metric_name].append({
                "value": record.metric_value,
                "recorded_at": record.created_at.isoformat(),
                "source": record.source,
            })
        
        # Calculate totals
        totals = {}
        for metric_name, values in metrics.items():
            totals[metric_name] = sum(v["value"] for v in values)
        
        return {
            "tenant_id": tenant_id,
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat(),
            "metrics": metrics,
            "totals": totals,
            "record_count": len(records),
        }
