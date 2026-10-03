from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.payment_method import PaymentMethod
from app.core.exceptions import ResourceNotFoundException, ValidationException


class PaymentMethodRepository:
    """Repository for PaymentMethod operations"""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
    
    def get_by_id(self, payment_method_id: str, tenant_id: str) -> PaymentMethod:
        """Get payment method by ID (tenant-scoped)"""
        method = self.db_session.query(PaymentMethod).filter_by(
            id=payment_method_id,
            tenant_id=tenant_id
        ).first()
        if not method:
            raise ResourceNotFoundException(f"Payment method {payment_method_id} not found")
        return method
    
    def get_by_stripe_id(self, stripe_payment_method_id: str) -> Optional[PaymentMethod]:
        """Get payment method by Stripe ID"""
        return self.db_session.query(PaymentMethod).filter_by(
            stripe_payment_method_id=stripe_payment_method_id
        ).first()
    
    def get_default_method(self, tenant_id: str) -> Optional[PaymentMethod]:
        """Get default payment method for tenant"""
        return self.db_session.query(PaymentMethod).filter_by(
            tenant_id=tenant_id,
            is_default=True,
            is_active=True
        ).first()
    
    def list_by_tenant(self, tenant_id: str) -> List[PaymentMethod]:
        """List all payment methods for tenant"""
        return self.db_session.query(PaymentMethod).filter_by(
            tenant_id=tenant_id,
            is_active=True
        ).order_by(PaymentMethod.is_default.desc(), PaymentMethod.created_at.desc()).all()
    
    def create(self, payment_method_data: dict) -> PaymentMethod:
        """Create a new payment method"""
        # If this is the first method, make it default
        existing_count = self.db_session.query(PaymentMethod).filter_by(
            tenant_id=payment_method_data.get("tenant_id"),
            is_active=True
        ).count()
        
        if existing_count == 0:
            payment_method_data["is_default"] = True
        
        method = PaymentMethod(**payment_method_data)
        self.db_session.add(method)
        self.db_session.flush()
        return method
    
    def set_as_default(self, payment_method_id: str, tenant_id: str) -> PaymentMethod:
        """Set a payment method as default"""
        method = self.get_by_id(payment_method_id, tenant_id)
        
        # Clear previous default
        self.db_session.query(PaymentMethod).filter_by(
            tenant_id=tenant_id,
            is_default=True
        ).update({"is_default": False})
        
        method.is_default = True
        self.db_session.flush()
        return method
    
    def deactivate(self, payment_method_id: str, tenant_id: str) -> PaymentMethod:
        """Deactivate a payment method"""
        method = self.get_by_id(payment_method_id, tenant_id)
        
        # If this is the default, set another as default
        if method.is_default:
            other_methods = self.db_session.query(PaymentMethod).filter(
                PaymentMethod.tenant_id == tenant_id,
                PaymentMethod.id != payment_method_id,
                PaymentMethod.is_active == True
            ).first()
            
            if other_methods:
                other_methods.is_default = True
            method.is_default = False
        
        method.is_active = False
        self.db_session.flush()
        return method
    
    def mark_invalid(self, payment_method_id: str, tenant_id: str) -> PaymentMethod:
        """Mark a payment method as invalid"""
        method = self.get_by_id(payment_method_id, tenant_id)
        method.is_valid = False
        self.db_session.flush()
        return method
    
    def update(self, payment_method_id: str, tenant_id: str, payment_data: dict) -> PaymentMethod:
        """Update a payment method"""
        method = self.get_by_id(payment_method_id, tenant_id)
        for key, value in payment_data.items():
            if key != "is_default":  # Use set_as_default for changing default
                setattr(method, key, value)
        self.db_session.flush()
        return method
