from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.models.invoice import Invoice, InvoiceStatus
from app.core.exceptions import ResourceNotFoundException, ValidationException


class InvoiceRepository:
    """Repository for Invoice operations"""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
    
    def get_by_id(self, invoice_id: str, tenant_id: str) -> Invoice:
        """Get invoice by ID (tenant-scoped)"""
        invoice = self.db_session.query(Invoice).filter_by(
            id=invoice_id,
            tenant_id=tenant_id
        ).first()
        if not invoice:
            raise ResourceNotFoundException(f"Invoice {invoice_id} not found")
        return invoice
    
    def get_by_number(self, invoice_number: str, tenant_id: str) -> Optional[Invoice]:
        """Get invoice by invoice number (tenant-scoped)"""
        return self.db_session.query(Invoice).filter_by(
            invoice_number=invoice_number,
            tenant_id=tenant_id
        ).first()
    
    def get_by_stripe_id(self, stripe_invoice_id: str) -> Optional[Invoice]:
        """Get invoice by Stripe ID"""
        return self.db_session.query(Invoice).filter_by(
            stripe_invoice_id=stripe_invoice_id
        ).first()
    
    def list_by_tenant(self, tenant_id: str, status: Optional[InvoiceStatus] = None) -> List[Invoice]:
        """List invoices for tenant"""
        query = self.db_session.query(Invoice).filter_by(tenant_id=tenant_id)
        if status:
            query = query.filter_by(status=status)
        return query.order_by(Invoice.issue_date.desc()).all()
    
    def list_by_subscription(self, subscription_id: str, tenant_id: str) -> List[Invoice]:
        """List invoices for a subscription (tenant-scoped)"""
        return self.db_session.query(Invoice).filter_by(
            subscription_id=subscription_id,
            tenant_id=tenant_id
        ).order_by(Invoice.issue_date.desc()).all()
    
    def list_overdue(self, tenant_id: Optional[str] = None) -> List[Invoice]:
        """List overdue invoices"""
        query = self.db_session.query(Invoice).filter(
            Invoice.status == InvoiceStatus.OVERDUE
        )
        if tenant_id:
            query = query.filter_by(tenant_id=tenant_id)
        return query.all()
    
    def list_pending_retry(self) -> List[Invoice]:
        """List invoices pending retry"""
        return self.db_session.query(Invoice).filter(
            Invoice.status.in_([InvoiceStatus.FAILED, InvoiceStatus.OVERDUE]),
            Invoice.next_retry_at <= datetime.utcnow()
        ).all()
    
    def create(self, invoice_data: dict) -> Invoice:
        """Create a new invoice"""
        invoice = Invoice(**invoice_data)
        self.db_session.add(invoice)
        self.db_session.flush()
        return invoice
    
    def update(self, invoice_id: str, tenant_id: str, invoice_data: dict) -> Invoice:
        """Update an invoice"""
        invoice = self.get_by_id(invoice_id, tenant_id)
        for key, value in invoice_data.items():
            setattr(invoice, key, value)
        self.db_session.flush()
        return invoice
    
    def mark_sent(self, invoice_id: str, tenant_id: str) -> Invoice:
        """Mark invoice as sent"""
        invoice = self.get_by_id(invoice_id, tenant_id)
        invoice.status = InvoiceStatus.SENT
        invoice.sent_at = datetime.utcnow()
        self.db_session.flush()
        return invoice
    
    def mark_paid(self, invoice_id: str, tenant_id: str, amount: float) -> Invoice:
        """Mark invoice as paid (fully or partially)"""
        invoice = self.get_by_id(invoice_id, tenant_id)
        invoice.paid_amount = amount
        invoice.status = InvoiceStatus.PAID if amount >= invoice.total_amount else InvoiceStatus.PENDING
        invoice.paid_at = datetime.utcnow()
        self.db_session.flush()
        return invoice
    
    def mark_failed(self, invoice_id: str, tenant_id: str) -> Invoice:
        """Mark invoice payment as failed"""
        invoice = self.get_by_id(invoice_id, tenant_id)
        invoice.status = InvoiceStatus.FAILED
        invoice.retry_count += 1
        invoice.last_retry_at = datetime.utcnow()
        
        # Schedule next retry (exponential backoff: 1h, 6h, 24h)
        retry_delays = [1, 6, 24]  # hours
        if invoice.retry_count <= len(retry_delays):
            next_retry_hours = retry_delays[invoice.retry_count - 1]
            invoice.next_retry_at = datetime.utcnow() + timedelta(hours=next_retry_hours)
        
        self.db_session.flush()
        return invoice
    
    def mark_overdue(self, invoice_id: str, tenant_id: str) -> Invoice:
        """Mark invoice as overdue"""
        invoice = self.get_by_id(invoice_id, tenant_id)
        invoice.status = InvoiceStatus.OVERDUE
        self.db_session.flush()
        return invoice
    
    def mark_refunded(self, invoice_id: str, tenant_id: str) -> Invoice:
        """Mark invoice as refunded"""
        invoice = self.get_by_id(invoice_id, tenant_id)
        invoice.status = InvoiceStatus.REFUNDED
        invoice.paid_amount = 0
        self.db_session.flush()
        return invoice
