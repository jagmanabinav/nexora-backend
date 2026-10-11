from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.subscription import Subscription, SubscriptionStatus


def subscription_expired(session: Session, tenant_id: UUID) -> bool:
    subscription = (
        session.query(Subscription)
        .filter(
            Subscription.tenant_id == tenant_id,
            Subscription.status.in_(
                [SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL]
            ),
        )
        .order_by(Subscription.created_at.desc())
        .first()
    )
    if subscription is None:
        return False
    period_end = subscription.current_period_end
    if period_end.tzinfo is None:
        period_end = period_end.replace(tzinfo=timezone.utc)
    return period_end <= datetime.now(timezone.utc)
