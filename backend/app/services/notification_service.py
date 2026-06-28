"""
notification_service.py
────────────────────────
Create, list, and mark notifications for users.
Used by the evaluation pipeline to notify students.
"""

import logging
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from sqlalchemy import select, update

from app.models.notification import Notification, NotificationType

logger = logging.getLogger(__name__)


# ── Sync version (for Celery workers) ────────────────────────

def create_notification_sync(
    db:          Session,
    user_id:     int,
    title:       str,
    message:     str,
    notif_type:  NotificationType = NotificationType.general,
    link:        str | None       = None,
) -> Notification:
    notif = Notification(
        user_id = user_id,
        type    = notif_type,
        title   = title,
        message = message,
        link    = link,
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)
    logger.info(
        "Notification created for user %d: %s", user_id, title
    )
    return notif


# ── Async version (for FastAPI routes) ───────────────────────

async def create_notification(
    db:         AsyncSession,
    user_id:    int,
    title:      str,
    message:    str,
    notif_type: NotificationType = NotificationType.general,
    link:       str | None       = None,
) -> Notification:
    notif = Notification(
        user_id = user_id,
        type    = notif_type,
        title   = title,
        message = message,
        link    = link,
    )
    db.add(notif)
    await db.flush()
    await db.refresh(notif)
    return notif


async def get_user_notifications(
    db:          AsyncSession,
    user_id:     int,
    unread_only: bool = False,
    limit:       int  = 50,
) -> list[Notification]:
    q = select(Notification).where(Notification.user_id == user_id)
    if unread_only:
        q = q.where(Notification.is_read == False)   # noqa: E712
    q = q.order_by(Notification.created_at.desc()).limit(limit)
    result = await db.execute(q)
    return result.scalars().all()


async def mark_read(
    db:      AsyncSession,
    user_id: int,
    notif_id: int | None = None,   # None = mark all
) -> int:
    """Mark one or all notifications as read. Returns count updated."""
    q = (
        update(Notification)
        .where(Notification.user_id == user_id, Notification.is_read == False)  # noqa
    )
    if notif_id is not None:
        q = q.where(Notification.id == notif_id)
    q = q.values(is_read=True)
    result = await db.execute(q)
    return result.rowcount


async def unread_count(db: AsyncSession, user_id: int) -> int:
    from sqlalchemy import func
    result = await db.execute(
        select(func.count(Notification.id)).where(
            Notification.user_id == user_id,
            Notification.is_read == False,   # noqa
        )
    )
    return result.scalar_one()