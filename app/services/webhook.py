import asyncio
import httpx
import json
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from app.models.webhook import WebhookDelivery, WebhookEventType
from app.repositories.webhook import WebhookEndpointRepository, WebhookDeliveryRepository
from app.core.dependencies import get_db_session


class WebhookService:
    """Service for managing webhooks and delivering events"""
    
    def __init__(self, session):
        self.session = session
        self.endpoint_repo = WebhookEndpointRepository(session)
        self.delivery_repo = WebhookDeliveryRepository(session)
        self.http_timeout = 30.0
        self.max_concurrent_deliveries = 5
    
    async def trigger_event(
        self,
        tenant_id: str,
        event_type: str,
        event_id: str,
        event_data: Dict[str, Any],
    ) -> None:
        """Trigger a webhook event and queue deliveries"""
        # Find endpoints that should receive this event
        endpoints = self.endpoint_repo.find_endpoints_for_event(tenant_id, event_type)
        
        if not endpoints:
            return
        
        # Create delivery records for each endpoint
        for endpoint in endpoints:
            payload = {
                "id": event_id,
                "type": event_type,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": event_data,
            }
            
            self.delivery_repo.create(
                endpoint_id=endpoint.id,
                event_type=event_type,
                event_id=event_id,
                payload=payload,
                max_attempts=endpoint.max_retries,
            )
        
        self.session.commit()
        
        # Start delivery attempts (fire and forget)
        asyncio.create_task(self._process_deliveries(endpoints))
    
    async def _process_deliveries(self, endpoints):
        """Process webhook deliveries"""
        tasks = []
        for endpoint in endpoints:
            deliveries = self.delivery_repo.list_pending_for_endpoint(
                endpoint.id,
                limit=10,
            )
            for delivery in deliveries:
                tasks.append(self._deliver_webhook(endpoint, delivery))
        
        # Process concurrently
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _deliver_webhook(self, endpoint, delivery: WebhookDelivery) -> None:
        """Deliver a single webhook"""
        try:
            async with httpx.AsyncClient(timeout=self.http_timeout) as client:
                # Prepare headers
                headers = {
                    "Content-Type": "application/json",
                    "User-Agent": "Nexora/1.0",
                }
                
                # Add custom headers from endpoint config
                if endpoint.headers:
                    headers.update(endpoint.headers)
                
                # Add signature
                payload_json = json.dumps(delivery.payload, default=str)
                signature = endpoint.get_signature(payload_json)
                headers["X-Webhook-Signature"] = f"sha256={signature}"
                
                # Send request
                response = await client.post(
                    endpoint.url,
                    content=payload_json,
                    headers=headers,
                )
                
                # Mark as sent if successful
                if 200 <= response.status_code < 300:
                    self.delivery_repo.mark_sent(
                        delivery.id,
                        response.status_code,
                        response.text[:1000],
                    )
                else:
                    self.delivery_repo.mark_failed(
                        delivery.id,
                        f"HTTP {response.status_code}: {response.text[:500]}",
                        response.status_code,
                    )
        
        except asyncio.TimeoutError:
            self.delivery_repo.mark_failed(
                delivery.id,
                "Request timeout",
            )
        except Exception as e:
            self.delivery_repo.mark_failed(
                delivery.id,
                f"Delivery error: {str(e)[:500]}",
            )
        
        self.session.commit()
    
    async def retry_failed_deliveries(self, batch_size: int = 50) -> int:
        """Retry failed webhook deliveries"""
        deliveries = self.delivery_repo.list_ready_for_retry(limit=batch_size)
        
        count = 0
        for delivery in deliveries:
            endpoint = delivery.endpoint
            await self._deliver_webhook(endpoint, delivery)
            count += 1
        
        return count
    
    def get_endpoint(self, tenant_id: str, endpoint_id: str):
        """Get a webhook endpoint"""
        return self.endpoint_repo.get_by_id(tenant_id, endpoint_id)
    
    def create_endpoint(
        self,
        tenant_id: str,
        name: str,
        url: str,
        events: List[str],
        description: str = None,
        headers: dict = None,
    ):
        """Create a new webhook endpoint"""
        return self.endpoint_repo.create(
            tenant_id=tenant_id,
            name=name,
            url=url,
            events=events,
            description=description,
            headers=headers,
        )
    
    def update_endpoint(
        self,
        tenant_id: str,
        endpoint_id: str,
        name: str = None,
        url: str = None,
        events: List[str] = None,
        description: str = None,
        is_active: bool = None,
        headers: dict = None,
    ):
        """Update a webhook endpoint"""
        return self.endpoint_repo.update(
            tenant_id=tenant_id,
            endpoint_id=endpoint_id,
            name=name,
            url=url,
            events=events,
            description=description,
            is_active=is_active,
            headers=headers,
        )
    
    def delete_endpoint(self, tenant_id: str, endpoint_id: str) -> bool:
        """Delete a webhook endpoint"""
        return self.endpoint_repo.delete(tenant_id, endpoint_id)
    
    def list_endpoints(self, tenant_id: str) -> List:
        """List all webhook endpoints for a tenant"""
        return self.endpoint_repo.list_by_tenant(tenant_id)
    
    def get_deliveries(
        self,
        endpoint_id: str,
        status: str = None,
        limit: int = 50,
        offset: int = 0,
    ):
        """Get deliveries for an endpoint"""
        return self.delivery_repo.list_by_endpoint(
            endpoint_id=endpoint_id,
            status=status,
            limit=limit,
            offset=offset,
        )
    
    def cleanup_old_deliveries(self, days_to_keep: int = 30) -> int:
        """Clean up old webhook deliveries"""
        return self.delivery_repo.cleanup_old_deliveries(days_to_keep)
