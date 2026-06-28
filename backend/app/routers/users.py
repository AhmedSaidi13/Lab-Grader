"""
users.py — Profile, avatar, student list
"""

import logging
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel, EmailStr

from app.database import get_db
from app.models.user import User, UserRole
from app.models.submission import Submission, SubmissionStatus
from app.models.assignment import Assignment
from app.utils.security import (
    get_current_user, require_teacher,
    hash_password, verify_password,
)
from app.utils.file_utils import save_upload

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/users", tags=["Users"])


# ── Schemas ───────────────────────────────────────────────────

class UpdateProfileRequest(BaseModel):
    email:            EmailStr | None = None
    current_password: str      | None = None
    new_password:     str      | None = None


class ProfileResponse(BaseModel):
    id:          int
    username:    str
    email:       str
    full_name:   str
    role:        str
    is_active:   bool
    avatar_path: str | None = None

    model_config = {"from_attributes": True}


# ── Profile ───────────────────────────────────────────────────

@router.get("/profile", response_model=ProfileResponse)
async def get_profile(current_user=Depends(get_current_user)):
    return current_user


@router.patch("/profile", response_model=ProfileResponse)
async def update_profile(
    payload:      UpdateProfileRequest,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    if payload.email and payload.email != current_user.email:
        result = await db.execute(
            select(User).where(
                User.email == payload.email,
                User.id    != current_user.id,
            )
        )
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email already in use")
        current_user.email = payload.email

    if payload.new_password:
        if not payload.current_password:
            raise HTTPException(
                status_code=400,
                detail="current_password is required",
            )
        if not verify_password(payload.current_password, current_user.hashed_password):
            raise HTTPException(
                status_code=400,
                detail="Current password is incorrect",
            )
        if len(payload.new_password) < 8:
            raise HTTPException(
                status_code=400,
                detail="Password must be at least 8 characters",
            )
        current_user.hashed_password = hash_password(payload.new_password)

    await db.flush()
    await db.refresh(current_user)
    return current_user


# ── Avatar ────────────────────────────────────────────────────

@router.post("/profile/avatar", response_model=ProfileResponse)
async def upload_avatar(
    file:         UploadFile  = File(...),
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    """Upload or replace profile photo. Accepts JPG, PNG, WEBP. Max 2MB."""
    from app.config import get_settings
    settings = get_settings()

    # Validate type
    ext = Path(file.filename).suffix.lower() if file.filename else ""
    if ext not in (".jpg", ".jpeg", ".png", ".webp"):
        raise HTTPException(
            status_code=400,
            detail="Only JPG, PNG, and WEBP images are accepted",
        )

    # Read and size-check (2 MB max for avatars)
    content = await file.read()
    if len(content) > 2 * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail="Avatar must be under 2MB",
        )

    # Delete old avatar
    if current_user.avatar_path:
        old = Path(current_user.avatar_path)
        if old.exists():
            old.unlink()

    # Save new avatar
    import uuid, aiofiles
    dest_dir = settings.upload_path / "avatars"
    dest_dir.mkdir(parents=True, exist_ok=True)
    unique_name = f"{current_user.id}_{uuid.uuid4().hex[:8]}{ext}"
    dest_path   = dest_dir / unique_name

    async with aiofiles.open(dest_path, "wb") as f:
        await f.write(content)

    current_user.avatar_path = str(dest_path)
    await db.flush()
    await db.refresh(current_user)
    logger.info("User %d uploaded avatar: %s", current_user.id, dest_path)
    return current_user


@router.get("/profile/avatar")
async def get_my_avatar(current_user: User = Depends(get_current_user)):
    if not current_user.avatar_path:
        raise HTTPException(status_code=404, detail="No avatar set")
    p = Path(current_user.avatar_path)
    if not p.exists():
        raise HTTPException(status_code=404, detail="Avatar file not found")
    return FileResponse(str(p))


@router.get("/{user_id}/avatar")
async def get_user_avatar(
    user_id: int,
    db:      AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user   = result.scalar_one_or_none()
    if not user or not user.avatar_path:
        raise HTTPException(status_code=404, detail="No avatar")
    p = Path(user.avatar_path)
    if not p.exists():
        raise HTTPException(status_code=404, detail="Avatar file not found")
    return FileResponse(str(p))


# ── Student list ──────────────────────────────────────────────

@router.get("/students", response_model=list)
async def list_students(
    db:      AsyncSession = Depends(get_db),
    teacher: User         = Depends(require_teacher),
):
    result   = await db.execute(
        select(User)
        .where(User.role == UserRole.student)
        .order_by(User.full_name)
    )
    students = result.scalars().all()

    student_list = []
    for student in students:
        sub_count = await db.execute(
            select(func.count(Submission.id))
            .where(Submission.student_id == student.id)
        )
        total_subs = sub_count.scalar_one()

        best_scores = await db.execute(
            select(
                Submission.assignment_id,
                func.max(Submission.score).label("best_score"),
            )
            .where(
                Submission.student_id == student.id,
                Submission.status     == SubmissionStatus.completed,
            )
            .group_by(Submission.assignment_id)
        )
        rows   = best_scores.all()
        scores = [r.best_score for r in rows if r.best_score is not None]

        student_list.append({
            "id":                    student.id,
            "username":              student.username,
            "full_name":             student.full_name,
            "email":                 student.email,
            "is_active":             student.is_active,
            "avatar_path":           student.avatar_path,
            "total_submissions":     total_subs,
            "assignments_attempted": len(rows),
            "average_score": round(sum(scores) / len(scores), 2) if scores else None,
        })

    return student_list


@router.get("/students/{student_id}/scores")
async def student_scores(
    student_id: int,
    db:         AsyncSession = Depends(get_db),
    teacher:    User         = Depends(require_teacher),
):
    result  = await db.execute(select(User).where(User.id == student_id))
    student = result.scalar_one_or_none()
    if not student or student.role != UserRole.student:
        raise HTTPException(status_code=404, detail="Student not found")

    assignments_result = await db.execute(
        select(Assignment)
        .where(Assignment.is_published == True)   # noqa: E712
        .order_by(Assignment.created_at)
    )
    assignments = assignments_result.scalars().all()

    scores = []
    for a in assignments:
        best = await db.execute(
            select(Submission)
            .where(
                Submission.student_id    == student_id,
                Submission.assignment_id == a.id,
                Submission.status        == SubmissionStatus.completed,
            )
            .order_by(Submission.score.desc())
            .limit(1)
        )
        best_sub = best.scalar_one_or_none()

        count_r  = await db.execute(
            select(func.count(Submission.id)).where(
                Submission.student_id    == student_id,
                Submission.assignment_id == a.id,
            )
        )
        attempts = count_r.scalar_one()

        scores.append({
            "assignment_id":    a.id,
            "assignment_title": a.title,
            "max_score":        a.max_score,
            "passing_score":    a.passing_score,
            "deadline":         a.deadline.isoformat() if a.deadline else None,
            "attempts":         attempts,
            "best_score":       best_sub.score if best_sub else None,
            "submission_id":    best_sub.id    if best_sub else None,
            "is_late":          best_sub.is_late if best_sub else False,
            "evaluated_at":     (
                best_sub.evaluated_at.isoformat()
                if best_sub and best_sub.evaluated_at else None
            ),
            "passed": (
                best_sub.score >= a.passing_score
                if best_sub and best_sub.score is not None else False
            ),
        })

    total_score = sum(s["best_score"] for s in scores if s["best_score"] is not None)
    total_max   = sum(s["max_score"]  for s in scores if s["best_score"] is not None)

    return {
        "student": {
            "id":          student.id,
            "username":    student.username,
            "full_name":   student.full_name,
            "email":       student.email,
            "avatar_path": student.avatar_path,
        },
        "summary": {
            "total_score":       round(total_score, 2),
            "total_max":         round(total_max, 2),
            "pass_count":        sum(1 for s in scores if s["passed"]),
            "total_assignments": len(assignments),
            "completion_rate":   round(
                sum(1 for s in scores if s["attempts"] > 0)
                / len(assignments) * 100 if assignments else 0, 1
            ),
        },
        "scores": scores,
    }