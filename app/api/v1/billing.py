from fastapi import APIRouter, Depends, status, HTTPException
from typing import List, Optional
from app.core.dependencies import get_current_user_with_roles
from app.core.authorization import require_permission
from app.core.exceptions import ValidationException, ResourceNotFoundException
from app.schemas.billing import (
    PlanResponse, PlanCreate, PlanUpdate,
    SubscriptionResponse, SubscriptionCreate, SubscriptionUpdate,
    InvoiceResponse,
    UsageRecordResponse,
    PaymentMethodResponse, PaymentMethodCreate,
    BillingOverviewResponse, CurrentUsageResponse,
    UpgradeSubscriptionRequest, DowngradeSubscriptionRequest,
    CancelSubscriptionRequest, PaymentRecordRequest, TrackUsageRequest,
)
from app.services.billing import BillingService
from app.services.invoice import InvoiceService
from app.services.usage import UsageService
from app.repositories.payment_method import PaymentMethodRepository
from app.repositories.plan import PlanRepository
from sqlalchemy.orm import Session
from app.core.dependencies import get_db, RequestContext


router = APIRouter(tags=["billing"])


# Plans endpoints
@router.get("/plans", response_model=List[PlanResponse])
def list_plans(db: Session = Depends(get_db)):
    """List all available pricing plans"""
    try:
        plan_repo = PlanRepository(db)
        plans = plan_repo.list()
        return plans
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/plans/{plan_id}", response_model=PlanResponse)
def get_plan(plan_id: str, db: Session = Depends(get_db)):
    """Get a specific plan"""
    try:
        plan_repo = PlanRepository(db)
        plan = plan_repo.get_by_id(plan_id)
        return plan
    except ResourceNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/plans", response_model=PlanResponse, status_code=status.HTTP_201_CREATED)
@require_permission("admin:plan:create")
def create_plan(
    plan_data: PlanCreate,
    current_user: RequestContext = Depends(get_current_user_with_roles),
    db: Session = Depends(get_db)
):
    """Create a new pricing plan (admin only)"""
    try:
        plan_repo = PlanRepository(db)
        plan = plan_repo.create(plan_data.dict())
        db.commit()
        return plan
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/plans/{plan_id}", response_model=PlanResponse)
@require_permission("admin:plan:update")
def update_plan(
    plan_id: str,
    plan_data: PlanUpdate,
    current_user: RequestContext = Depends(get_current_user_with_roles),
    db: Session = Depends(get_db)
):
    """Update a pricing plan (admin only)"""
    try:
        plan_repo = PlanRepository(db)
        plan = plan_repo.update(plan_id, plan_data.dict(exclude_unset=True))
        db.commit()
        return plan
    except ResourceNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# Subscriptions endpoints
@router.post("/subscriptions", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED)
def create_subscription(
    subscription_data: SubscriptionCreate,
    current_user: RequestContext = Depends(get_current_user_with_roles),
    db: Session = Depends(get_db)
):
    """Create a new subscription for current tenant"""
    try:
        billing_service = BillingService(db)
        subscription = billing_service.create_subscription(
            tenant_id=current_user.tenant_id,
            plan_id=subscription_data.plan_id,
            billing_cycle=subscription_data.billing_cycle,
            trial_days=subscription_data.trial_days,
        )
        return subscription
    except ValidationException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ResourceNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/subscriptions", response_model=SubscriptionResponse)
def get_subscription(
    current_user: RequestContext = Depends(get_current_user_with_roles),
    db: Session = Depends(get_db)
):
    """Get current tenant's active subscription"""
    try:
        subscription_repo = __import__("app.repositories.subscription", fromlist=["SubscriptionRepository"]).SubscriptionRepository(db)
        subscription = subscription_repo.get_any_active_subscription(current_user.tenant_id)
        if not subscription:
            raise HTTPException(status_code=404, detail="No active subscription found")
        return subscription
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/subscriptions", response_model=SubscriptionResponse)
def update_subscription(
    subscription_data: SubscriptionUpdate,
    current_user: RequestContext = Depends(get_current_user_with_roles),
    db: Session = Depends(get_db)
):
    """Update current subscription"""
    try:
        subscription_repo = __import__("app.repositories.subscription", fromlist=["SubscriptionRepository"]).SubscriptionRepository(db)
        subscription = subscription_repo.get_any_active_subscription(current_user.tenant_id)
        if not subscription:
            raise HTTPException(status_code=404, detail="No active subscription found")
        
        subscription = subscription_repo.update(subscription.id, current_user.tenant_id, subscription_data.dict(exclude_unset=True))
        db.commit()
        return subscription
    except ValidationException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/subscriptions/upgrade", response_model=dict)
def upgrade_subscription(
    upgrade_data: UpgradeSubscriptionRequest,
    current_user: RequestContext = Depends(get_current_user_with_roles),
    db: Session = Depends(get_db)
):
    """Upgrade subscription to a higher tier"""
    try:
        subscription_repo = __import__("app.repositories.subscription", fromlist=["SubscriptionRepository"]).SubscriptionRepository(db)
        subscription = subscription_repo.get_any_active_subscription(current_user.tenant_id)
        if not subscription:
            raise HTTPException(status_code=404, detail="No active subscription found")
        
        billing_service = BillingService(db)
        subscription, invoice = billing_service.upgrade_subscription(
            subscription_id=subscription.id,
            tenant_id=current_user.tenant_id,
            new_plan_id=upgrade_data.new_plan_id,
            proration_credits=upgrade_data.proration_credits
        )
        
        return {
            "subscription": SubscriptionResponse.model_validate(subscription).model_dump(mode="json"),
            "invoice": InvoiceResponse.model_validate(invoice).model_dump(mode="json") if invoice else None,
            "message": "Subscription upgraded successfully"
        }
    except ValidationException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ResourceNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/subscriptions/downgrade", response_model=SubscriptionResponse)
def downgrade_subscription(
    downgrade_data: DowngradeSubscriptionRequest,
    current_user: RequestContext = Depends(get_current_user_with_roles),
    db: Session = Depends(get_db)
):
    """Downgrade subscription to a lower tier (effective next billing cycle)"""
    try:
        subscription_repo = __import__("app.repositories.subscription", fromlist=["SubscriptionRepository"]).SubscriptionRepository(db)
        subscription = subscription_repo.get_any_active_subscription(current_user.tenant_id)
        if not subscription:
            raise HTTPException(status_code=404, detail="No active subscription found")
        
        billing_service = BillingService(db)
        subscription = billing_service.downgrade_subscription(
            subscription_id=subscription.id,
            tenant_id=current_user.tenant_id,
            new_plan_id=downgrade_data.new_plan_id
        )
        return subscription
    except ValidationException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ResourceNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/subscriptions/cancel", response_model=SubscriptionResponse)
def cancel_subscription(
    cancel_data: CancelSubscriptionRequest,
    current_user: RequestContext = Depends(get_current_user_with_roles),
    db: Session = Depends(get_db)
):
    """Cancel current subscription"""
    try:
        subscription_repo = __import__("app.repositories.subscription", fromlist=["SubscriptionRepository"]).SubscriptionRepository(db)
        subscription = subscription_repo.get_any_active_subscription(current_user.tenant_id)
        if not subscription:
            raise HTTPException(status_code=404, detail="No active subscription found")
        
        billing_service = BillingService(db)
        subscription = billing_service.cancel_subscription(
            subscription_id=subscription.id,
            tenant_id=current_user.tenant_id,
            reason=cancel_data.reason,
            effective_immediately=cancel_data.effective_immediately
        )
        return subscription
    except ValidationException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# Invoices endpoints
@router.get("/invoices", response_model=List[InvoiceResponse])
def list_invoices(
    status: Optional[str] = None,
    limit: int = 50,
    current_user: RequestContext = Depends(get_current_user_with_roles),
    db: Session = Depends(get_db)
):
    """List invoices for current tenant"""
    try:
        invoice_service = InvoiceService(db)
        invoices = invoice_service.list_invoices(
            tenant_id=current_user.tenant_id,
            status=status,
            limit=limit
        )
        return invoices
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
def get_invoice(
    invoice_id: str,
    current_user: RequestContext = Depends(get_current_user_with_roles),
    db: Session = Depends(get_db)
):
    """Get a specific invoice"""
    try:
        invoice_service = InvoiceService(db)
        invoice = invoice_service.get_invoice(invoice_id, current_user.tenant_id)
        return invoice
    except ResourceNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/invoices/{invoice_id}/payment", response_model=dict)
def record_payment(
    invoice_id: str,
    payment_data: PaymentRecordRequest,
    current_user: RequestContext = Depends(get_current_user_with_roles),
    db: Session = Depends(get_db)
):
    """Record a payment for an invoice"""
    try:
        invoice_service = InvoiceService(db)
        invoice = invoice_service.record_payment(
            invoice_id=invoice_id,
            tenant_id=current_user.tenant_id,
            amount=payment_data.amount,
            payment_method=payment_data.payment_method
        )
        return {
            "invoice": InvoiceResponse.model_validate(invoice).model_dump(mode="json"),
            "message": "Payment recorded successfully"
        }
    except ValidationException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ResourceNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/invoices/{invoice_id}/retry", response_model=dict)
def retry_payment(
    invoice_id: str,
    current_user: RequestContext = Depends(get_current_user_with_roles),
    db: Session = Depends(get_db)
):
    """Retry payment for a failed invoice"""
    try:
        invoice_service = InvoiceService(db)
        invoice = invoice_service.retry_failed_payment(invoice_id, current_user.tenant_id)
        return {
            "invoice": InvoiceResponse.model_validate(invoice).model_dump(mode="json"),
            "message": "Payment retry initiated"
        }
    except ValidationException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ResourceNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# Usage endpoints
@router.get("/usage", response_model=CurrentUsageResponse)
def get_current_usage(
    current_user: RequestContext = Depends(get_current_user_with_roles),
    db: Session = Depends(get_db)
):
    """Get current usage metrics"""
    try:
        usage_service = UsageService(db)
        usage = usage_service.get_current_usage(current_user.tenant_id)
        return usage
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/usage/track", response_model=UsageRecordResponse, status_code=status.HTTP_201_CREATED)
def track_usage(
    usage_data: TrackUsageRequest,
    current_user: RequestContext = Depends(get_current_user_with_roles),
    db: Session = Depends(get_db)
):
    """Track resource usage"""
    try:
        usage_service = UsageService(db)
        record = usage_service.track_usage(
            tenant_id=current_user.tenant_id,
            metric_name=usage_data.metric_name,
            amount=usage_data.amount,
            description=usage_data.description
        )
        return record
    except ValidationException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/usage/limits", response_model=dict)
def check_usage_limits(
    current_user: RequestContext = Depends(get_current_user_with_roles),
    db: Session = Depends(get_db)
):
    """Check if tenant has exceeded usage limits"""
    try:
        usage_service = UsageService(db)
        limits = usage_service.check_usage_limits(current_user.tenant_id)
        return limits
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Billing overview
@router.get("/billing/overview", response_model=dict)
def get_billing_overview(
    current_user: RequestContext = Depends(get_current_user_with_roles),
    db: Session = Depends(get_db)
):
    """Get billing overview for current tenant"""
    try:
        billing_service = BillingService(db)
        overview = billing_service.get_billing_overview(current_user.tenant_id)
        return overview
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Payment methods endpoints
@router.get("/payment-methods", response_model=List[PaymentMethodResponse])
def list_payment_methods(
    current_user: RequestContext = Depends(get_current_user_with_roles),
    db: Session = Depends(get_db)
):
    """List payment methods for current tenant"""
    try:
        payment_repo = PaymentMethodRepository(db)
        methods = payment_repo.list_by_tenant(current_user.tenant_id)
        return methods
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/payment-methods/{method_id}/default", response_model=PaymentMethodResponse)
def set_default_payment_method(
    method_id: str,
    current_user: RequestContext = Depends(get_current_user_with_roles),
    db: Session = Depends(get_db)
):
    """Set a payment method as default"""
    try:
        payment_repo = PaymentMethodRepository(db)
        method = payment_repo.set_as_default(method_id, current_user.tenant_id)
        db.commit()
        return method
    except ResourceNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/payment-methods/{method_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_payment_method(
    method_id: str,
    current_user: RequestContext = Depends(get_current_user_with_roles),
    db: Session = Depends(get_db)
):
    """Delete a payment method"""
    try:
        payment_repo = PaymentMethodRepository(db)
        payment_repo.deactivate(method_id, current_user.tenant_id)
        db.commit()
        return None
    except ResourceNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
