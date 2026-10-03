from datetime import datetime, timedelta
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from app.models.invoice import Invoice, InvoiceStatus
from app.repositories.invoice import InvoiceRepository
from app.repositories.subscription import SubscriptionRepository
from app.core.exceptions import ValidationException, ResourceNotFoundException


class InvoiceService:
    """Service for invoice operations"""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.invoice_repo = InvoiceRepository(db_session)
        self.subscription_repo = SubscriptionRepository(db_session)
    
    def get_invoice(self, invoice_id: str, tenant_id: str) -> Invoice:
        """Get invoice by ID"""
        return self.invoice_repo.get_by_id(invoice_id, tenant_id)
    
    def list_invoices(
        self,
        tenant_id: str,
        status: Optional[InvoiceStatus] = None,
        limit: int = 50
    ) -> List[Invoice]:
        """List invoices for a tenant"""
        invoices = self.invoice_repo.list_by_tenant(tenant_id, status)
        return invoices[:limit]
    
    def get_invoice_details(self, invoice_id: str, tenant_id: str) -> Dict:
        """Get detailed invoice information"""
        invoice = self.invoice_repo.get_by_id(invoice_id, tenant_id)
        subscription = self.subscription_repo.get_by_id(invoice.subscription_id, tenant_id)
        
        return {
            "id": str(invoice.id),
            "invoice_number": invoice.invoice_number,
            "status": invoice.status.value,
            "issue_date": invoice.issue_date.isoformat(),
            "due_date": invoice.due_date.isoformat(),
            "sent_at": invoice.sent_at.isoformat() if invoice.sent_at else None,
            "paid_at": invoice.paid_at.isoformat() if invoice.paid_at else None,
            "subtotal": invoice.subtotal,
            "tax_amount": invoice.tax_amount,
            "discount_amount": invoice.discount_amount,
            "total_amount": invoice.total_amount,
            "paid_amount": invoice.paid_amount,
            "remaining_balance": invoice.remaining_balance(),
            "description": invoice.description,
            "subscription_id": str(subscription.id),
            "is_overdue": invoice.is_overdue(),
        }
    
    def record_payment(
        self,
        invoice_id: str,
        tenant_id: str,
        amount: float,
        payment_method: str = "stripe"
    ) -> Invoice:
        """Record a payment for an invoice"""
        
        invoice = self.invoice_repo.get_by_id(invoice_id, tenant_id)
        
        if invoice.status in [InvoiceStatus.PAID, InvoiceStatus.REFUNDED]:
            raise ValidationException(f"Invoice is already {invoice.status.value}")
        
        if amount <= 0:
            raise ValidationException("Payment amount must be greater than 0")
        
        if amount > invoice.remaining_balance():
            raise ValidationException(f"Payment amount exceeds remaining balance of {invoice.remaining_balance()}")
        
        invoice = self.invoice_repo.mark_paid(invoice_id, tenant_id, amount)
        
        # Reset retry count on successful payment
        invoice.retry_count = 0
        invoice.last_retry_at = None
        invoice.next_retry_at = None
        
        self.db_session.commit()
        return invoice
    
    def retry_failed_payment(self, invoice_id: str, tenant_id: str) -> Invoice:
        """Retry payment for a failed invoice"""
        
        invoice = self.invoice_repo.get_by_id(invoice_id, tenant_id)
        
        if not invoice.can_retry():
            raise ValidationException("Invoice has exceeded maximum retry attempts")
        
        if invoice.status not in [InvoiceStatus.FAILED, InvoiceStatus.OVERDUE]:
            raise ValidationException("Only failed or overdue invoices can be retried")
        
        invoice = self.invoice_repo.mark_failed(invoice_id, tenant_id)
        self.db_session.commit()
        return invoice
    
    def mark_overdue(self, invoice_id: str, tenant_id: str) -> Invoice:
        """Mark an invoice as overdue"""
        invoice = self.invoice_repo.get_by_id(invoice_id, tenant_id)
        invoice = self.invoice_repo.mark_overdue(invoice_id, tenant_id)
        self.db_session.commit()
        return invoice
    
    def refund_invoice(self, invoice_id: str, tenant_id: str) -> Invoice:
        """Refund an invoice"""
        invoice = self.invoice_repo.get_by_id(invoice_id, tenant_id)
        
        if invoice.status != InvoiceStatus.PAID:
            raise ValidationException("Only paid invoices can be refunded")
        
        invoice = self.invoice_repo.mark_refunded(invoice_id, tenant_id)
        self.db_session.commit()
        return invoice
    
    def send_invoice(self, invoice_id: str, tenant_id: str) -> Invoice:
        """Mark invoice as sent"""
        invoice = self.invoice_repo.get_by_id(invoice_id, tenant_id)
        invoice = self.invoice_repo.mark_sent(invoice_id, tenant_id)
        
        # TODO: Implement email sending
        # email_service.send_invoice(invoice)
        
        self.db_session.commit()
        return invoice
    
    def get_overdue_invoices(self, tenant_id: Optional[str] = None) -> List[Invoice]:
        """Get all overdue invoices"""
        return self.invoice_repo.list_overdue(tenant_id)
    
    def get_invoices_pending_retry(self) -> List[Invoice]:
        """Get invoices pending retry"""
        return self.invoice_repo.list_pending_retry()
    
    def process_pending_retries(self) -> Dict[str, int]:
        """Process all pending invoice retries (called by background job)"""
        invoices = self.get_invoices_pending_retry()
        
        results = {
            "total": len(invoices),
            "succeeded": 0,
            "failed": 0,
        }
        
        for invoice in invoices:
            try:
                # TODO: Call Stripe to retry payment
                # if payment succeeds:
                #   invoice = self.record_payment(invoice.id, invoice.tenant_id, invoice.total_amount)
                #   results["succeeded"] += 1
                # else:
                #   invoice = self.invoice_repo.mark_failed(invoice.id, invoice.tenant_id)
                #   results["failed"] += 1
                pass
            except Exception as e:
                results["failed"] += 1
        
        self.db_session.commit()
        return results
