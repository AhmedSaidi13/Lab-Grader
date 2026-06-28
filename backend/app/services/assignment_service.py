from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException
from datetime import datetime, timezone

from app.models.assignment import Assignment
from app.models.user import User
from app.schemas.assignment import AssignmentCreate, AssignmentUpdate


async def create_assignment(
    db: AsyncSession, payload: AssignmentCreate, teacher: User
) -> Assignment:
    data             = payload.model_dump()
    data["max_score"]= 20.0   # always /20
    assignment       = Assignment(**data, created_by_id=teacher.id)
    db.add(assignment)
    await db.flush()
    await db.refresh(assignment)
    return assignment


async def get_assignment(db: AsyncSession, assignment_id: int) -> Assignment:
    result = await db.execute(
        select(Assignment).where(Assignment.id == assignment_id)
    )
    a = result.scalar_one_or_none()
    if not a:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return a


async def list_assignments(
    db: AsyncSession, published_only: bool = True
) -> list[Assignment]:
    q = select(Assignment)
    if published_only:
        q = q.where(Assignment.is_published == True)  # noqa: E712
    q = q.order_by(Assignment.created_at.desc())
    result = await db.execute(q)
    return result.scalars().all()


async def update_assignment(
    db: AsyncSession,
    assignment_id: int,
    payload: AssignmentUpdate,
    teacher: User,
) -> Assignment:
    a = await get_assignment(db, assignment_id)
    if a.created_by_id != teacher.id and teacher.role != "admin":
        raise HTTPException(status_code=403, detail="Not your assignment")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(a, field, value)
    await db.flush()
    await db.refresh(a)
    return a


async def delete_assignment(
    db: AsyncSession, assignment_id: int, teacher: User
) -> None:
    a = await get_assignment(db, assignment_id)
    if a.created_by_id != teacher.id and teacher.role != "admin":
        raise HTTPException(status_code=403, detail="Not your assignment")
    await db.delete(a)


async def is_deadline_passed(assignment: Assignment) -> tuple[bool, bool]:
    """Returns (is_late, can_submit)."""
    if not assignment.deadline:
        return False, True
    now      = datetime.now(timezone.utc)
    deadline = assignment.deadline
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)
    is_late   = now > deadline
    can_submit= not is_late or assignment.allow_late_submission
    return is_late, can_submit