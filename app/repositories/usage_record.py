from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import datetime
from app.models.usage_record import UsageRecord
from app.core.exceptions import ResourceNotFoundException


class UsageRecordRepository:
    """Repository for UsageRecord operations"""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
    
    def get_by_id(self, usage_id: str, tenant_id: str) -> UsageRecord:
        """Get usage record by ID (tenant-scoped)"""
        record = self.db_session.query(UsageRecord).filter_by(
            id=usage_id,
            tenant_id=tenant_id
        ).first()
        if not record:
            raise ResourceNotFoundException(f"Usage record {usage_id} not found")
        return record
    
    def get_current_usage(
        self,
        tenant_id: str,
        metric_name: str,
        period_start: datetime,
        period_end: datetime
    ) -> Optional[UsageRecord]:
        """Get usage record for current billing period"""
        return self.db_session.query(UsageRecord).filter_by(
            tenant_id=tenant_id,
            metric_name=metric_name,
            billing_period_start=period_start,
            billing_period_end=period_end
        ).first()
    
    def list_by_tenant(self, tenant_id: str) -> List[UsageRecord]:
        """List all usage records for tenant"""
        return self.db_session.query(UsageRecord).filter_by(
            tenant_id=tenant_id
        ).order_by(UsageRecord.billing_period_start.desc()).all()
    
    def list_by_subscription(self, subscription_id: str, tenant_id: str) -> List[UsageRecord]:
        """List usage records for a subscription (tenant-scoped)"""
        return self.db_session.query(UsageRecord).filter_by(
            subscription_id=subscription_id,
            tenant_id=tenant_id
        ).order_by(UsageRecord.billing_period_start.desc()).all()
    
    def list_by_metric(
        self,
        tenant_id: str,
        metric_name: str,
        period_start: datetime,
        period_end: datetime
    ) -> List[UsageRecord]:
        """List usage records for a metric in a period"""
        return self.db_session.query(UsageRecord).filter(
            UsageRecord.tenant_id == tenant_id,
            UsageRecord.metric_name == metric_name,
            UsageRecord.billing_period_start >= period_start,
            UsageRecord.billing_period_end <= period_end
        ).order_by(UsageRecord.created_at).all()
    
    def create(self, usage_data: dict) -> UsageRecord:
        """Create a new usage record"""
        record = UsageRecord(**usage_data)
        self.db_session.add(record)
        self.db_session.flush()
        return record
    
    def update(self, usage_id: str, tenant_id: str, usage_data: dict) -> UsageRecord:
        """Update a usage record"""
        record = self.get_by_id(usage_id, tenant_id)
        for key, value in usage_data.items():
            setattr(record, key, value)
        self.db_session.flush()
        return record
    
    def increment_usage(
        self,
        tenant_id: str,
        metric_name: str,
        amount: float,
        period_start: datetime,
        period_end: datetime
    ) -> UsageRecord:
        """Increment usage for a metric"""
        record = self.get_current_usage(tenant_id, metric_name, period_start, period_end)
        
        if not record:
            # Create new record
            record = UsageRecord(
                tenant_id=tenant_id,
                metric_name=metric_name,
                metric_value=amount,
                billing_period_start=period_start,
                billing_period_end=period_end,
                source="system"
            )
            self.db_session.add(record)
        else:
            # Increment existing record
            record.metric_value += amount
        
        self.db_session.flush()
        return record
    
    def reset_period(
        self,
        tenant_id: str,
        metric_name: str,
        period_start: datetime,
        period_end: datetime
    ) -> None:
        """Reset usage for a new billing period"""
        self.db_session.query(UsageRecord).filter(
            UsageRecord.tenant_id == tenant_id,
            UsageRecord.metric_name == metric_name,
            UsageRecord.billing_period_start < period_start
        ).delete()
        self.db_session.flush()
    
    def get_total_usage(
        self,
        tenant_id: str,
        metric_name: str,
        period_start: datetime,
        period_end: datetime
    ) -> float:
        """Get total usage for a metric in a period"""
        records = self.list_by_metric(tenant_id, metric_name, period_start, period_end)
        return sum(r.metric_value for r in records)
