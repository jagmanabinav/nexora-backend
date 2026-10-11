"""Tenant-scoped FabWash GST invoices."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.authorization import require_permission
from app.core.dependencies import RequestContext, get_current_user_with_roles, get_db_session
from app.core.exceptions import ResourceNotFoundException, ValidationException
from app.models.tenant import Tenant
from app.schemas.fabwash_invoice import FabWashInvoiceCreate, FabWashInvoiceResponse
from app.services.fabwash_invoice import FabWashInvoiceService

router = APIRouter(prefix="/fabwash/invoices", tags=["FabWash invoices"])


def _require_fabwash_tenant(context: RequestContext, session: Session) -> None:
    tenant = session.query(Tenant).filter(Tenant.id == context.tenant_id).first()
    if tenant is None or tenant.status != "ACTIVE":
        raise HTTPException(status_code=403, detail="Active tenant access is required")


@router.get("", response_model=list[FabWashInvoiceResponse])
@require_permission("billing:read")
def list_invoices(
    current_user: RequestContext = Depends(get_current_user_with_roles),
    session: Session = Depends(get_db_session),
):
    _require_fabwash_tenant(current_user, session)
    return FabWashInvoiceService(session).list_for_tenant(current_user.tenant_id)


@router.get("/{invoice_id}", response_model=FabWashInvoiceResponse)
@require_permission("billing:read")
def get_invoice(
    invoice_id: UUID,
    current_user: RequestContext = Depends(get_current_user_with_roles),
    session: Session = Depends(get_db_session),
):
    _require_fabwash_tenant(current_user, session)
    try:
        return FabWashInvoiceService(session).get_for_tenant(
            invoice_id, current_user.tenant_id
        )
    except ResourceNotFoundException as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post(
    "",
    response_model=FabWashInvoiceResponse,
    status_code=status.HTTP_201_CREATED,
)
@require_permission("billing:update")
def issue_invoice(
    request: FabWashInvoiceCreate,
    current_user: RequestContext = Depends(get_current_user_with_roles),
    session: Session = Depends(get_db_session),
):
    _require_fabwash_tenant(current_user, session)
    try:
        invoice = FabWashInvoiceService(session).issue(
            current_user.tenant_id, request
        )
        session.commit()
        session.refresh(invoice)
        return invoice
    except (ResourceNotFoundException, ValidationException) as error:
        session.rollback()
        raise HTTPException(status_code=422, detail=str(error)) from error
    except Exception:
        session.rollback()
        raise
