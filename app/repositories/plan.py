from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.plan import Plan, PlanTier
from app.core.exceptions import ResourceNotFoundException


class PlanRepository:
    """Repository for Plan operations"""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
    
    def get_by_id(self, plan_id: str) -> Plan:
        """Get plan by ID"""
        plan = self.db_session.query(Plan).filter_by(id=plan_id, is_active=True).first()
        if not plan:
            raise ResourceNotFoundException(f"Plan {plan_id} not found")
        return plan
    
    def get_by_slug(self, slug: str) -> Plan:
        """Get plan by slug"""
        plan = self.db_session.query(Plan).filter_by(slug=slug, is_active=True).first()
        if not plan:
            raise ResourceNotFoundException(f"Plan with slug {slug} not found")
        return plan
    
    def list(self) -> List[Plan]:
        """List all active plans ordered by display_order"""
        return self.db_session.query(Plan).filter_by(is_active=True).order_by(Plan.display_order).all()
    
    def list_by_tier(self, tier: PlanTier) -> List[Plan]:
        """List plans by tier"""
        return self.db_session.query(Plan).filter_by(tier=tier, is_active=True).order_by(Plan.display_order).all()
    
    def get_default_plan(self) -> Plan:
        """Get the default plan (free tier)"""
        plan = self.db_session.query(Plan).filter_by(is_default=True, is_active=True).first()
        if not plan:
            raise ResourceNotFoundException("No default plan found")
        return plan
    
    def create(self, plan_data: dict) -> Plan:
        """Create a new plan"""
        plan = Plan(**plan_data)
        self.db_session.add(plan)
        self.db_session.flush()
        return plan
    
    def update(self, plan_id: str, plan_data: dict) -> Plan:
        """Update an existing plan"""
        plan = self.get_by_id(plan_id)
        for key, value in plan_data.items():
            setattr(plan, key, value)
        self.db_session.flush()
        return plan
    
    def delete(self, plan_id: str) -> None:
        """Soft delete a plan by marking as inactive"""
        plan = self.get_by_id(plan_id)
        plan.is_active = False
        self.db_session.flush()
