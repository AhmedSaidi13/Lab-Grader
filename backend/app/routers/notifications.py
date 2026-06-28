"""
notifications.py — student notification endpoints
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.utils.security import get_current_user
from app.services.notification_service import (
    get_user_notifications,
    mark_read,
    unread_count,
)

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("")
async def list_notifications(
    unread_only:  bool = Query(False),
    limit:        int  = Query(50, ge=1, le=100),
    db:           AsyncSession  = Depends(get_db),
    current_user=Depends(get_current_user),
):
    notifications = await get_user_notifications(
        db, current_user.id, unread_only=unread_only, limit=limit
    )
    return [
        {
            "id":         n.id,
            "type":       n.type,
            "title":      n.title,
            "message":    n.message,
            "is_read":    n.is_read,
            "link":       n.link,
            "created_at": n.created_at.isoformat(),
        }
        for n in notifications
    ]


@router.get("/unread-count")
async def get_unread_count(
    db:           AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    count = await unread_count(db, current_user.id)
    return {"count": count}


@router.patch("/{notif_id}/read")
async def mark_one_read(
    notif_id:     int,
    db:           AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    await mark_read(db, current_user.id, notif_id)
    return {"message": "Marked as read"}


@router.patch("/read-all")
async def mark_all_read(
    db:           AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    count = await mark_read(db, current_user.id)
    return {"message": f"Marked {count} notifications as read"}