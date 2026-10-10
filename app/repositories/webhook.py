from typing import List, Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.webhook import WebhookEndpoint, WebhookDelivery, WebhookEventType
from uuid import uuid4 as generate_id


class WebhookEndpointRepository:
    """Repository for webhook endpoints"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create(
        self,
        tenant_id: str,
        name: str,
        url: str,
        events: List[str],
        description: str = None,
        secret: str = None,
        max_retries: int = 3,
        retry_delay_seconds: int = 300,
        headers: dict = None,
    ) -> WebhookEndpoint:
        """Create a new webhook endpoint"""
        if secret is None:
            import secrets
            secret = secrets.token_urlsafe(32)
        
        endpoint = WebhookEndpoint(
            id=generate_id(),
            tenant_id=tenant_id,
            name=name,
            url=url,
            events=events,
            description=description,
            secret=secret,
            max_retries=max_retries,
            retry_delay_seconds=retry_delay_seconds,
            headers=headers or {},
        )
        
        self.session.add(endpoint)
        self.session.flush()
        return endpoint
    
    def get_by_id(self, tenant_id: str, endpoint_id: str) -> Optional[WebhookEndpoint]:
        """Get webhook endpoint by ID"""
        return self.session.query(WebhookEndpoint).filter(
            WebhookEndpoint.tenant_id == tenant_id,
            WebhookEndpoint.id == endpoint_id,
        ).first()
    
    def list_by_tenant(self, tenant_id: str, active_only: bool = False) -> List[WebhookEndpoint]:
        """List all webhook endpoints for a tenant"""
        query = self.session.query(WebhookEndpoint).filter(
            WebhookEndpoint.tenant_id == tenant_id
        )
        
        if active_only:
            query = query.filter(WebhookEndpoint.is_active == True)
        
        return query.order_by(WebhookEndpoint.created_at.desc()).all()
    
    def find_endpoints_for_event(self, tenant_id: str, event_type: str) -> List[WebhookEndpoint]:
        """Find all active endpoints that should receive an event"""
        endpoints = self.list_by_tenant(tenant_id, active_only=True)
        return [e for e in endpoints if e.should_deliver_event(event_type)]
    
    def update(
        self,
        tenant_id: str,
        endpoint_id: str,
        name: str = None,
        url: str = None,
        events: List[str] = None,
        description: str = None,
        is_active: bool = None,
        max_retries: int = None,
        retry_delay_seconds: int = None,
        headers: dict = None,
    ) -> Optional[WebhookEndpoint]:
        """Update a webhook endpoint"""
        endpoint = self.get_by_id(tenant_id, endpoint_id)
        if not endpoint:
            return None
        
        if name is not None:
            endpoint.name = name
        if url is not None:
            endpoint.url = url
        if events is not None:
            endpoint.events = events
        if description is not None:
            endpoint.description = description
        if is_active is not None:
            endpoint.is_active = is_active
        if max_retries is not None:
            endpoint.max_retries = max_retries
        if retry_delay_seconds is not None:
            endpoint.retry_delay_seconds = retry_delay_seconds
        if headers is not None:
            endpoint.headers = headers
        
        self.session.flush()
        return endpoint
    
    def delete(self, tenant_id: str, endpoint_id: str) -> bool:
        """Delete a webhook endpoint"""
        endpoint = self.get_by_id(tenant_id, endpoint_id)
        if not endpoint:
            return False
        
        self.session.delete(endpoint)
        self.session.flush()
        return True


class WebhookDeliveryRepository:
    """Repository for webhook deliveries"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create(
        self,
        endpoint_id: str,
        event_type: str,
        event_id: str,
        payload: dict,
        max_attempts: int = 3,
    ) -> WebhookDelivery:
        """Create a new webhook delivery record"""
        delivery = WebhookDelivery(
            id=generate_id(),
            endpoint_id=endpoint_id,
            event_type=event_type,
            event_id=event_id,
            payload=payload,
            max_attempts=max_attempts,
            status="pending",
        )
        
        self.session.add(delivery)
        self.session.flush()
        return delivery
    
    def get_by_id(self, delivery_id: str) -> Optional[WebhookDelivery]:
        """Get webhook delivery by ID"""
        return self.session.query(WebhookDelivery).filter(
            WebhookDelivery.id == delivery_id
        ).first()
    
    def list_pending_for_endpoint(self, endpoint_id: str, limit: int = 100) -> List[WebhookDelivery]:
        """List pending deliveries for an endpoint"""
        return self.session.query(WebhookDelivery).filter(
            WebhookDelivery.endpoint_id == endpoint_id,
            WebhookDelivery.status.in_(["pending", "failed"]),
        ).order_by(WebhookDelivery.created_at.asc()).limit(limit).all()
    
    def list_ready_for_retry(self, limit: int = 100) -> List[WebhookDelivery]:
        """List deliveries that are ready for retry"""
        now = datetime.now(timezone.utc)
        return self.session.query(WebhookDelivery).filter(
            WebhookDelivery.status.in_(["pending", "failed"]),
            or_(
                WebhookDelivery.next_retry_at.is_(None),
                WebhookDelivery.next_retry_at <= now,
            ),
        ).order_by(WebhookDelivery.created_at.asc()).limit(limit).all()
    
    def list_by_endpoint(
        self,
        endpoint_id: str,
        status: str = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[List[WebhookDelivery], int]:
        """List deliveries for an endpoint with pagination"""
        query = self.session.query(WebhookDelivery).filter(
            WebhookDelivery.endpoint_id == endpoint_id
        )
        
        if status:
            query = query.filter(WebhookDelivery.status == status)
        
        total = query.count()
        deliveries = query.order_by(
            WebhookDelivery.created_at.desc()
        ).offset(offset).limit(limit).all()
        
        return deliveries, total
    
    def mark_sent(self, delivery_id: str, http_status: int, response: str = None) -> Optional[WebhookDelivery]:
        """Mark delivery as successfully sent"""
        delivery = self.get_by_id(delivery_id)
        if not delivery:
            return None
        
        delivery.mark_sent(http_status, response)
        self.session.flush()
        return delivery
    
    def mark_failed(self, delivery_id: str, error: str, http_status: int = None) -> Optional[WebhookDelivery]:
        """Mark delivery as failed"""
        delivery = self.get_by_id(delivery_id)
        if not delivery:
            return None
        
        delivery.mark_failed(error, http_status)
        self.session.flush()
        return delivery
    
    def cleanup_old_deliveries(self, days_to_keep: int = 30) -> int:
        """Delete old completed deliveries"""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
        
        result = self.session.query(WebhookDelivery).filter(
            WebhookDelivery.status.in_(["sent", "exhausted"]),
            WebhookDelivery.completed_at < cutoff_date,
        ).delete(synchronize_session=False)
        
        self.session.flush()
        return result
