"""
submission_service.py
─────────────────────
- One active submission per student per assignment
- Replace files before deadline (version increments)
- Multi-file support based on assignment.max_files
- Bulk evaluation triggered by task scheduler (not on submit)
"""

import uuid
import aiofiles
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.submission import Submission, SubmissionStatus
from app.models.assignment import Assignment
from app.models.user import User, UserRole
from app.services.assignment_service import get_assignment, is_deadline_passed
from app.config import get_settings

settings = get_settings()
logger   = logging.getLogger(__name__)


# ── File helpers ──────────────────────────────────────────────

def _c_extension(filename: str) -> bool:
    return Path(filename).suffix.lower() == ".c"


async def _save_c_file(content: bytes, assignment_id: int, student_id: int) -> str:
    """Save a .c file to disk. Returns absolute path string."""
    dest_dir = settings.upload_path / "submissions" / str(assignment_id) / str(student_id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    unique_name = f"{uuid.uuid4().hex}.c"
    dest_path   = dest_dir / unique_name
    async with aiofiles.open(dest_path, "wb") as f:
        await f.write(content)
    return str(dest_path)


def _delete_file(path: str) -> None:
    p = Path(path)
    if p.exists():
        try:
            p.unlink()
        except Exception as exc:
            logger.warning("Could not delete file %s: %s", path, exc)


async def _read_upload(file: UploadFile, max_bytes: int) -> bytes:
    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail=f"File '{file.filename}' is empty")
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File '{file.filename}' exceeds "
                   f"{settings.MAX_FILE_SIZE_MB}MB limit",
        )
    return content


# ── Submit (create or replace) ────────────────────────────────

async def submit_or_replace(
    db:            AsyncSession,
    assignment_id: int,
    files:         list[UploadFile],
    student:       User,
) -> Submission:
    """
    Create a new submission OR replace files of the existing one.

    Rules:
    - Student can submit/replace up to assignment.max_files .c files
    - Only one active submission per student per assignment
    - Replacing is allowed before the deadline (resets status to pending)
    - After deadline: no new submissions, no replacements
    """
    assignment: Assignment = await get_assignment(db, assignment_id)

    if not assignment.is_published:
        raise HTTPException(status_code=403, detail="Assignment is not published")

    # Deadline check
    is_late, can_submit = await is_deadline_passed(assignment)
    if not can_submit:
        raise HTTPException(
            status_code=403,
            detail="Submission deadline has passed",
        )

    # File count check
    max_files = assignment.max_files or 1
    if len(files) == 0:
        raise HTTPException(status_code=400, detail="No files provided")
    if len(files) > max_files:
        raise HTTPException(
            status_code=400,
            detail=f"This assignment accepts at most {max_files} file(s). "
                   f"You uploaded {len(files)}.",
        )

    # Validate all files are .c
    for f in files:
        if not f.filename:
            raise HTTPException(status_code=400, detail="File has no name")
        if not _c_extension(f.filename):
            raise HTTPException(
                status_code=400,
                detail=f"Only .c files are accepted. Got: {f.filename}",
            )

    # Read all file contents first (validates size)
    file_contents: list[tuple[bytes, str]] = []
    for f in files:
        content = await _read_upload(f, settings.max_file_bytes)
        file_contents.append((content, f.filename))

    # Check for existing submission
    existing_result = await db.execute(
        select(Submission).where(
            Submission.assignment_id == assignment_id,
            Submission.student_id   == student.id,
        ).order_by(Submission.submitted_at.desc()).limit(1)
    )
    existing = existing_result.scalar_one_or_none()

    if existing:
        # ── Replace existing submission ───────────────────────
        if existing.status not in (
            SubmissionStatus.pending,
            SubmissionStatus.queued,
            SubmissionStatus.failed,
            SubmissionStatus.compile_error,
            SubmissionStatus.completed,
            SubmissionStatus.timeout,
        ):
            raise HTTPException(
                status_code=400,
                detail=f"Cannot replace a submission that is currently "
                       f"being evaluated (status: {existing.status}). "
                       "Please wait for evaluation to finish.",
            )

        # Delete old files from disk
        for file_info in (existing.files or []):
            _delete_file(file_info.get("path", ""))
        if existing.file_path:
            _delete_file(existing.file_path)

        # Save new files
        new_files = []
        for content, original_name in file_contents:
            path = await _save_c_file(content, assignment_id, student.id)
            new_files.append({"path": path, "original_filename": original_name})

        # Reset submission state
        existing.files             = new_files
        existing.file_path         = new_files[0]["path"]
        existing.original_filename = new_files[0]["original_filename"]
        existing.status            = SubmissionStatus.pending
        existing.is_late           = is_late
        existing.version           = (existing.version or 1) + 1
        existing.score             = None
        existing.compile_output    = None
        existing.test_results      = []
        existing.static_analysis   = {}
        existing.feedback          = None
        existing.celery_task_id    = None
        existing.evaluated_at      = None

        await db.flush()
        await db.refresh(existing)

        logger.info(
            "Student %d replaced submission for assignment %d (v%d)",
            student.id, assignment_id, existing.version,
        )
        return existing

    else:
        # ── Create new submission ─────────────────────────────
        new_files = []
        for content, original_name in file_contents:
            path = await _save_c_file(content, assignment_id, student.id)
            new_files.append({"path": path, "original_filename": original_name})

        submission = Submission(
            assignment_id     = assignment_id,
            student_id        = student.id,
            files             = new_files,
            file_path         = new_files[0]["path"],
            original_filename = new_files[0]["original_filename"],
            status            = SubmissionStatus.pending,
            is_late           = is_late,
            version           = 1,
            test_results      = [],
            static_analysis   = {},
        )
        db.add(submission)
        await db.flush()
        await db.refresh(submission)

        logger.info(
            "Student %d submitted %d file(s) for assignment %d",
            student.id, len(new_files), assignment_id,
        )
        return submission


# ── Read helpers ──────────────────────────────────────────────

async def get_submission(
    db:           AsyncSession,
    submission_id:int,
    current_user: User,
) -> Submission:
    result = await db.execute(
        select(Submission).where(Submission.id == submission_id)
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")
    if current_user.role == UserRole.student and sub.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return sub


async def get_my_submission(
    db:            AsyncSession,
    assignment_id: int,
    student:       User,
) -> Optional[Submission]:
    """Get the active submission for a student on an assignment (or None)."""
    result = await db.execute(
        select(Submission)
        .where(
            Submission.assignment_id == assignment_id,
            Submission.student_id   == student.id,
        )
        .order_by(Submission.submitted_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def list_my_submissions(
    db:            AsyncSession,
    student:       User,
    assignment_id: Optional[int] = None,
) -> list[Submission]:
    q = select(Submission).where(Submission.student_id == student.id)
    if assignment_id is not None:
        q = q.where(Submission.assignment_id == assignment_id)
    q = q.order_by(Submission.submitted_at.desc())
    result = await db.execute(q)
    return result.scalars().all()


async def list_assignment_submissions(
    db:            AsyncSession,
    assignment_id: int,
    teacher:       User,
) -> list[Submission]:
    assignment = await get_assignment(db, assignment_id)
    if assignment.created_by_id != teacher.id and teacher.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Not your assignment")
    result = await db.execute(
        select(Submission)
        .where(Submission.assignment_id == assignment_id)
        .order_by(Submission.submitted_at.desc())
    )
    return result.scalars().all()


async def delete_submission(
    db:            AsyncSession,
    submission_id: int,
    current_user:  User,
) -> None:
    sub = await get_submission(db, submission_id, current_user)

    # Only allow deletion if deadline hasn't passed
    assignment = await get_assignment(db, sub.assignment_id)
    is_late, _ = await is_deadline_passed(assignment)
    if is_late:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete a submission after the deadline has passed",
        )

    for file_info in (sub.files or []):
        _delete_file(file_info.get("path", ""))
    if sub.file_path:
        _delete_file(sub.file_path)

    await db.delete(sub)


async def get_submission_stats(
    db:            AsyncSession,
    assignment_id: int,
) -> dict:
    result = await db.execute(
        select(Submission).where(Submission.assignment_id == assignment_id)
    )
    subs = result.scalars().all()

    if not subs:
        return {
            "total": 0, "completed": 0, "pending": 0,
            "failed": 0, "average_score": None,
            "pass_rate": None, "late_count": 0,
        }

    assignment  = await get_assignment(db, assignment_id)
    completed   = [s for s in subs if s.status == SubmissionStatus.completed]
    scores      = [s.score for s in completed if s.score is not None]

    return {
        "total":         len(subs),
        "completed":     len(completed),
        "pending":       sum(1 for s in subs if s.status == SubmissionStatus.pending),
        "failed":        sum(1 for s in subs if s.status == SubmissionStatus.failed),
        "compile_error": sum(1 for s in subs if s.status == SubmissionStatus.compile_error),
        "average_score": round(sum(scores) / len(scores), 2) if scores else None,
        "pass_rate": (
            round(
                sum(1 for sc in scores if sc >= assignment.passing_score)
                / len(scores) * 100, 1,
            ) if scores else None
        ),
        "late_count": sum(1 for s in subs if s.is_late),
        "max_score":  assignment.max_score,
    }