"""
Application repository for data access.

Provides tenant-scoped application management.
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.application import Application
from app.core.exceptions import ResourceNotFoundException
from uuid import uuid4


class ApplicationRepository:
    """Repository for application data access with tenant scoping."""

    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        tenant_id: str,
        name: str,
        description: Optional[str] = None,
        webhook_url: Optional[str] = None,
    ) -> Application:
        """Create a new application for tenant."""
        app_id = uuid4()
        application = Application(
            id=app_id,
            tenant_id=tenant_id,
            name=name,
            description=description,
            webhook_url=webhook_url,
            status="draft",
        )
        self.session.add(application)
        self.session.flush()
        return application

    def get_by_id(self, app_id: str, tenant_id: str) -> Optional[Application]:
        """Get application by ID, scoped to tenant."""
        return self.session.query(Application).filter(
            and_(Application.id == app_id, Application.tenant_id == tenant_id)
        ).first()

    def get_by_name(self, tenant_id: str, name: str) -> Optional[Application]:
        """Get application by name, scoped to tenant."""
        return self.session.query(Application).filter(
            and_(Application.tenant_id == tenant_id, Application.name == name)
        ).first()

    def list_by_tenant(self, tenant_id: str, status: Optional[str] = None) -> List[Application]:
        """List all applications for tenant, optionally filtered by status."""
        query = self.session.query(Application).filter(Application.tenant_id == tenant_id)
        if status:
            query = query.filter(Application.status == status)
        return query.all()

    def update(self, app_id: str, tenant_id: str, **kwargs) -> Application:
        """Update application fields."""
        application = self.get_by_id(app_id, tenant_id)
        if not application:
            raise ResourceNotFoundException(f"Application {app_id} not found")

        for key, value in kwargs.items():
            if hasattr(application, key) and value is not None:
                setattr(application, key, value)

        self.session.flush()
        return application

    def set_status(self, app_id: str, tenant_id: str, status: str) -> Application:
        """Set application status."""
        return self.update(app_id, tenant_id, status=status)
