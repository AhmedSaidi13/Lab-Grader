"""
submissions.py
──────────────
- One submission per student (create or replace)
- Multi-file upload based on assignment.max_files
- No manual evaluation trigger — deadline scheduler handles it
- Students can replace before deadline
"""

import json as _json
from fastapi import APIRouter, Depends, UploadFile, File, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional, List

from app.database import get_db
from app.schemas.submission import SubmissionResponse, SubmissionListResponse
from app.services.submission_service import (
    submit_or_replace,
    get_submission,
    get_my_submission,
    list_my_submissions,
    list_assignment_submissions,
    delete_submission,
    get_submission_stats,
)
from app.utils.security import get_current_user, require_teacher

router = APIRouter(prefix="/submissions", tags=["Submissions"])


# ── Submit / replace ──────────────────────────────────────────

@router.post("", response_model=SubmissionResponse, status_code=201)
async def submit(
    assignment_id: int          = Query(...),
    files:         List[UploadFile] = File(...),
    db:            AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Submit or replace files for an assignment.

    - First call: creates a new submission (status=pending)
    - Subsequent calls before deadline: replaces files, resets status, bumps version
    - After deadline: rejected (evaluation runs automatically by scheduler)
    - Accepts 1 file (default) or up to assignment.max_files files
    """
    sub = await submit_or_replace(db, assignment_id, files, current_user)
    return sub


# ── Get my current submission for an assignment ───────────────

@router.get("/my-submission/{assignment_id}", response_model=Optional[SubmissionResponse])
async def my_submission_for_assignment(
    assignment_id: int,
    db:            AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get the student's current submission for a specific assignment, or null."""
    sub = await get_my_submission(db, assignment_id, current_user)
    return sub


# ── List all my submissions ───────────────────────────────────

@router.get("/mine", response_model=list[SubmissionListResponse])
async def my_submissions(
    assignment_id: Optional[int] = Query(None),
    db:            AsyncSession  = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await list_my_submissions(db, current_user, assignment_id)


# ── Get single submission ─────────────────────────────────────

@router.get("/{submission_id}", response_model=SubmissionResponse)
async def get_one(
    submission_id: int,
    db:            AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await get_submission(db, submission_id, current_user)


# ── Delete (only before deadline) ────────────────────────────

@router.delete("/{submission_id}", status_code=204)
async def delete_one(
    submission_id: int,
    db:            AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    await delete_submission(db, submission_id, current_user)


# ── Live status ───────────────────────────────────────────────

@router.get("/{submission_id}/status")
async def submission_status(
    submission_id: int,
    db:            AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    sub = await get_submission(db, submission_id, current_user)

    celery_info = {}
    if sub.celery_task_id:
        from app.workers.celery_app import celery_app as _celery
        from app.workers.tasks import get_task_progress
        task_result = _celery.AsyncResult(sub.celery_task_id)
        celery_info = {
            "task_id":    sub.celery_task_id,
            "task_state": task_result.state,
        }
        progress = get_task_progress(sub.celery_task_id)
        if progress:
            celery_info["progress"] = progress

    return {
        "submission_id": sub.id,
        "status":        sub.status,
        "version":       sub.version,
        "score":         sub.score,
        "evaluated_at":  sub.evaluated_at.isoformat() if sub.evaluated_at else None,
        "celery":        celery_info,
    }


# ── Full evaluation report ────────────────────────────────────

@router.get("/{submission_id}/report")
async def get_report(
    submission_id: int,
    db:            AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    from app.models.submission import SubmissionStatus
    from app.services.assignment_service import get_assignment

    sub = await get_submission(db, submission_id, current_user)

    if sub.status not in (
        SubmissionStatus.completed,
        SubmissionStatus.compile_error,
    ):
        raise HTTPException(
            status_code=400,
            detail=f"Submission not yet evaluated (status: {sub.status})",
        )

    assignment = await get_assignment(db, sub.assignment_id)

    return {
        "submission_id":     sub.id,
        "assignment_title":  assignment.title,
        "student_id":        sub.student_id,
        "files":             sub.files or [],
        "original_filename": sub.original_filename,
        "version":           sub.version,
        "submitted_at":      sub.submitted_at.isoformat(),
        "evaluated_at":      sub.evaluated_at.isoformat() if sub.evaluated_at else None,
        "is_late":           sub.is_late,
        "compile_output":    sub.compile_output,
        "score": {
            "final":   sub.score,
            "max":     20.0,
            "passing": assignment.passing_score,
        },
        "test_results":    sub.test_results    or [],
        "static_analysis": sub.static_analysis or {},
        "feedback":        sub.feedback,
    }


# ── Feedback ──────────────────────────────────────────────────

@router.get("/{submission_id}/feedback")
async def get_feedback(
    submission_id: int,
    db:            AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    from app.models.submission import SubmissionStatus
    sub = await get_submission(db, submission_id, current_user)

    if sub.status not in (
        SubmissionStatus.completed,
        SubmissionStatus.compile_error,
    ):
        raise HTTPException(
            status_code=400,
            detail=f"Not yet evaluated (status: {sub.status})",
        )
    if not sub.feedback:
        raise HTTPException(status_code=404, detail="No feedback available")

    try:
        return _json.loads(sub.feedback)
    except (_json.JSONDecodeError, TypeError):
        return {
            "summary":  sub.feedback,
            "sections": [{"title": "Feedback", "body": sub.feedback,
                          "level": "info", "code": None}],
            "generated_by_llm": False,
        }


# ── Teacher: all submissions for assignment ───────────────────

@router.get("/assignment/{assignment_id}", response_model=list[SubmissionResponse])
async def assignment_submissions(
    assignment_id: int,
    db:            AsyncSession = Depends(get_db),
    teacher=Depends(require_teacher),
):
    return await list_assignment_submissions(db, assignment_id, teacher)


# ── Teacher: stats ────────────────────────────────────────────

@router.get("/assignment/{assignment_id}/stats")
async def assignment_stats(
    assignment_id: int,
    db:            AsyncSession = Depends(get_db),
    teacher=Depends(require_teacher),
):
    return await get_submission_stats(db, assignment_id)


# ── Teacher: leaderboard ──────────────────────────────────────

@router.get("/assignment/{assignment_id}/leaderboard")
async def leaderboard(
    assignment_id: int,
    db:            AsyncSession = Depends(get_db),
    teacher=Depends(require_teacher),
):
    from app.models.submission import Submission, SubmissionStatus
    from app.models.user import User

    result = await db.execute(
        select(
            Submission.student_id,
            func.max(Submission.score).label("best_score"),
            func.count(Submission.id).label("attempts"),
        )
        .where(
            Submission.assignment_id == assignment_id,
            Submission.status        == SubmissionStatus.completed,
        )
        .group_by(Submission.student_id)
        .order_by(func.max(Submission.score).desc())
    )
    rows = result.all()

    leaderboard_rows = []
    for rank, row in enumerate(rows, start=1):
        user_r = await db.execute(select(User).where(User.id == row.student_id))
        user   = user_r.scalar_one_or_none()
        leaderboard_rows.append({
            "rank":       rank,
            "student_id": row.student_id,
            "full_name":  user.full_name if user else "Unknown",
            "username":   user.username  if user else "unknown",
            "best_score": row.best_score,
            "attempts":   row.attempts,
        })
    return leaderboard_rows


# ── Teacher: bulk re-evaluate ─────────────────────────────────

@router.post("/assignment/{assignment_id}/reevaluate")
async def bulk_reevaluate(
    assignment_id: int,
    _=Depends(require_teacher),
):
    from app.workers.tasks import bulk_reevaluate_task
    task = bulk_reevaluate_task.apply_async(
        args=[assignment_id], queue="evaluation"
    )
    return {"message": "Bulk re-evaluation started", "task_id": task.id}


# ── Task progress ─────────────────────────────────────────────

@router.get("/tasks/{task_id}/progress")
async def task_progress(
    task_id: str,
    _=Depends(get_current_user),
):
    from app.workers.celery_app import celery_app as _celery
    from app.workers.tasks import get_task_progress
    task_result = _celery.AsyncResult(task_id)
    progress    = get_task_progress(task_id)
    return {
        "task_id":  task_id,
        "state":    task_result.state,
        "progress": progress,
        "result":   task_result.result if task_result.ready() else None,
        "failed":   task_result.failed(),
    }


# ── Teacher: feedback override ────────────────────────────────

@router.patch("/{submission_id}/feedback")
async def override_feedback(
    submission_id: int,
    payload:       dict,
    db:            AsyncSession = Depends(get_db),
    teacher=Depends(require_teacher),
):
    sub         = await get_submission(db, submission_id, teacher)
    custom_text = payload.get("feedback", "").strip()
    if not custom_text:
        raise HTTPException(status_code=400, detail="feedback is required")

    override = {
        "summary":          custom_text,
        "generated_by_llm": False,
        "teacher_override": True,
        "sections": [{
            "title": "Teacher Feedback",
            "body":  custom_text,
            "level": "info",
            "code":  None,
        }],
    }
    sub.feedback = _json.dumps(override)
    await db.flush()
    return {"message": "Feedback updated"}