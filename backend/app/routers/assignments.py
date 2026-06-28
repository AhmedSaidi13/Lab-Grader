"""
assignments.py
──────────────
Full CRUD for assignments, file uploads, test generation,
and static analysis. max_score is always 20.0 — never from client.
Deadline validation only on write (create/update), never on read.
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional

from fastapi import (
    APIRouter, Depends, UploadFile, File,
    Query, HTTPException, Form,
)
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.assignment import Assignment
from app.schemas.assignment import (
    AssignmentCreate, AssignmentUpdate,
    AssignmentResponse, AssignmentListResponse,
)
from app.services.assignment_service import (
    create_assignment, get_assignment,
    list_assignments, update_assignment, delete_assignment,
)
from app.services.test_generator import generate_test_cases, generate_from_custom_inputs
from app.services.static_analysis import analyse_c_file, analysis_to_dict
from app.utils.security import get_current_user, require_teacher
from app.utils.file_utils import save_upload

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/assignments", tags=["Assignments"])


# ── Response builder (no Pydantic validators fired on read) ───

def _build_response(a: Assignment) -> AssignmentResponse:
    """
    Safely build AssignmentResponse from ORM object.
    Does NOT run deadline_must_be_future — deadline may be past
    when reading existing assignments.
    """
    return AssignmentResponse(
        id                      = a.id,
        title                   = a.title,
        description             = a.description,
        instructions            = a.instructions,
        deadline                = a.deadline,
        passing_score           = a.passing_score         or 10.0,
        allow_late_submission   = a.allow_late_submission or False,
        late_penalty_percent    = a.late_penalty_percent  or 20.0,
        max_files               = a.max_files             or 1,
        is_published            = a.is_published,
        max_score               = a.max_score             or 20.0,
        reference_solution_path = a.reference_solution_path,
        label_file_path         = a.label_file_path,
        assignment_file_path    = a.assignment_file_path,
        test_cases              = a.test_cases            or [],
        created_by_id           = a.created_by_id,
        created_at              = a.created_at,
        updated_at              = a.updated_at,
    )


# ════════════════════════════════════════════════════════════════
#  CRUD
# ════════════════════════════════════════════════════════════════

@router.post("", response_model=AssignmentResponse, status_code=201)
async def create(
    payload: AssignmentCreate,
    db:      AsyncSession = Depends(get_db),
    teacher=Depends(require_teacher),
):
    """Create a bare assignment (no files). max_score set to 20 automatically."""
    a = await create_assignment(db, payload, teacher)
    return _build_response(a)


@router.get("", response_model=list[AssignmentListResponse])
async def list_all(
    db:           AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    List assignments.
    Students see published only.
    Professors see all (published + drafts).
    """
    from app.models.user import UserRole
    published_only = current_user.role == UserRole.student
    assignments    = await list_assignments(db, published_only=published_only)

    result = []
    for a in assignments:
        try:
            result.append(
                AssignmentListResponse(
                    id              = a.id,
                    title           = a.title,
                    description     = a.description,
                    deadline        = a.deadline,
                    is_published    = a.is_published,
                    max_score       = a.max_score  or 20.0,
                    max_files       = a.max_files  or 1,
                    test_case_count = len(a.test_cases) if a.test_cases else 0,
                    created_at      = a.created_at,
                )
            )
        except Exception as exc:
            logger.error("Skipping assignment %d in list: %s", a.id, exc)
            continue

    return result


@router.get("/{assignment_id}", response_model=AssignmentResponse)
async def get_one(
    assignment_id: int,
    db:            AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """
    Get full assignment detail.
    Deadline is NOT validated on read — it may legitimately be in the past.
    """
    a = await get_assignment(db, assignment_id)
    return _build_response(a)


@router.patch("/{assignment_id}", response_model=AssignmentResponse)
async def update(
    assignment_id: int,
    payload:       AssignmentUpdate,
    db:            AsyncSession = Depends(get_db),
    teacher=Depends(require_teacher),
):
    """
    Update assignment fields.
    When is_published is set to True and a reference solution exists,
    test case generation is queued automatically in the background.
    """
    a = await update_assignment(db, assignment_id, payload, teacher)

    if payload.is_published is True and a.reference_solution_path:
        logger.info(
            "Assignment %d published — queuing test generation", assignment_id
        )
        from app.workers.tasks import generate_tests_task
        generate_tests_task.apply_async(
            args=[assignment_id], queue="generation"
        )

    return _build_response(a)


@router.delete("/{assignment_id}", status_code=204)
async def delete(
    assignment_id: int,
    db:            AsyncSession = Depends(get_db),
    teacher=Depends(require_teacher),
):
    """Delete an assignment and all associated metadata."""
    await delete_assignment(db, assignment_id, teacher)


# ════════════════════════════════════════════════════════════════
#  CREATE WITH FILES (single multipart request)
# ════════════════════════════════════════════════════════════════

@router.post("/create-with-files", response_model=AssignmentResponse, status_code=201)
async def create_with_files(
    title:                 str   = Form(...),
    description:           str   = Form(...),
    instructions:          str   = Form(""),
    passing_score:         float = Form(10.0),
    allow_late_submission: bool  = Form(False),
    late_penalty_percent:  float = Form(20.0),
    deadline:              str   = Form(""),
    max_files:             int   = Form(1),
    reference_solution:    Optional[UploadFile] = File(None),
    subject_file:          Optional[UploadFile] = File(None),
    label_file:            Optional[UploadFile] = File(None),
    db:                    AsyncSession = Depends(get_db),
    teacher=Depends(require_teacher),
):
    """
    Create an assignment and optionally attach files in one multipart request.

    - max_score is always 20.0 (do NOT send it from the frontend)
    - If a reference_solution (.c) is uploaded, test case generation
      is queued automatically in the background after creation
    - subject_file is downloadable by students
    - label_file is a cover image / PDF label
    """
    from datetime import datetime, timezone

    # ── Parse deadline (write-time validation) ────────────────
    parsed_deadline = None
    if deadline and deadline.strip():
        try:
            parsed_deadline = datetime.fromisoformat(
                deadline.replace("Z", "+00:00")
            )
            if parsed_deadline.tzinfo is None:
                parsed_deadline = parsed_deadline.replace(tzinfo=timezone.utc)
            if parsed_deadline <= datetime.now(timezone.utc):
                raise HTTPException(
                    status_code=422,
                    detail="Deadline must be in the future",
                )
        except HTTPException:
            raise
        except ValueError:
            parsed_deadline = None   # ignore malformed deadline

    # ── Validate max_files ────────────────────────────────────
    if max_files < 1 or max_files > 10:
        raise HTTPException(
            status_code=422,
            detail="max_files must be between 1 and 10",
        )

    # ── Build payload (no max_score — always 20) ──────────────
    payload = AssignmentCreate(
        title                 = title,
        description           = description,
        instructions          = instructions or None,
        passing_score         = passing_score,
        allow_late_submission = allow_late_submission,
        late_penalty_percent  = late_penalty_percent,
        deadline              = parsed_deadline,
        max_files             = max_files,
    )

    a = await create_assignment(db, payload, teacher)
    a.max_score = 20.0   # enforce — never from client

    # ── Upload reference solution ─────────────────────────────
    if reference_solution and reference_solution.filename:
        try:
            path, _ = await save_upload(
                reference_solution,
                f"solutions/{a.id}",
                [".c"],
            )
            a.reference_solution_path = path
            logger.info(
                "Reference solution attached to assignment %d: %s",
                a.id, path,
            )
        except Exception as exc:
            logger.warning(
                "Reference solution upload failed for assignment %d: %s",
                a.id, exc,
            )

    # ── Upload subject file ───────────────────────────────────
    if subject_file and subject_file.filename:
        try:
            path, _ = await save_upload(
                subject_file,
                f"subjects/{a.id}",
                [".pdf", ".txt", ".md"],
            )
            a.assignment_file_path = path
            logger.info(
                "Subject file attached to assignment %d: %s", a.id, path
            )
        except Exception as exc:
            logger.warning(
                "Subject file upload failed for assignment %d: %s",
                a.id, exc,
            )

    # ── Upload label / cover ──────────────────────────────────
    if label_file and label_file.filename:
        try:
            path, _ = await save_upload(
                label_file,
                f"labels/{a.id}",
                [".pdf", ".png", ".jpg", ".jpeg"],
            )
            a.label_file_path = path
            logger.info(
                "Label file attached to assignment %d: %s", a.id, path
            )
        except Exception as exc:
            logger.warning(
                "Label file upload failed for assignment %d: %s",
                a.id, exc,
            )

    await db.flush()
    await db.refresh(a)

    # ── Auto-queue test generation if reference uploaded ──────
    if a.reference_solution_path:
        logger.info(
            "Queuing automatic test generation for assignment %d", a.id
        )
        from app.workers.tasks import generate_tests_task
        generate_tests_task.apply_async(
            args=[a.id], queue="generation"
        )

    return _build_response(a)


# ════════════════════════════════════════════════════════════════
#  FILE UPLOADS (individual endpoints)
# ════════════════════════════════════════════════════════════════

@router.post("/{assignment_id}/reference-solution")
async def upload_reference_solution(
    assignment_id: int,
    file:          UploadFile   = File(...),
    db:            AsyncSession = Depends(get_db),
    teacher=Depends(require_teacher),
):
    """Upload or replace the reference solution (.c only)."""
    a = await get_assignment(db, assignment_id)

    # Delete old file if exists
    if a.reference_solution_path:
        old = Path(a.reference_solution_path)
        if old.exists():
            old.unlink()

    path, _ = await save_upload(file, f"solutions/{assignment_id}", [".c"])
    a.reference_solution_path = path
    await db.flush()

    logger.info(
        "Reference solution uploaded for assignment %d: %s",
        assignment_id, path,
    )
    return {
        "message": "Reference solution uploaded successfully",
        "path":    path,
    }


@router.post("/{assignment_id}/label")
async def upload_label(
    assignment_id: int,
    file:          UploadFile   = File(...),
    db:            AsyncSession = Depends(get_db),
    teacher=Depends(require_teacher),
):
    """Upload or replace the assignment label / cover image."""
    a = await get_assignment(db, assignment_id)

    if a.label_file_path:
        old = Path(a.label_file_path)
        if old.exists():
            old.unlink()

    path, _ = await save_upload(
        file,
        f"labels/{assignment_id}",
        [".pdf", ".png", ".jpg", ".jpeg"],
    )
    a.label_file_path = path
    await db.flush()

    return {"message": "Label uploaded successfully", "path": path}


@router.post("/{assignment_id}/subject-file")
async def upload_subject(
    assignment_id: int,
    file:          UploadFile   = File(...),
    db:            AsyncSession = Depends(get_db),
    teacher=Depends(require_teacher),
):
    """Upload or replace the downloadable subject / problem statement file."""
    a = await get_assignment(db, assignment_id)

    if a.assignment_file_path:
        old = Path(a.assignment_file_path)
        if old.exists():
            old.unlink()

    path, _ = await save_upload(
        file,
        f"subjects/{assignment_id}",
        [".pdf", ".txt", ".md"],
    )
    a.assignment_file_path = path
    await db.flush()

    return {"message": "Subject file uploaded successfully", "path": path}


@router.get("/{assignment_id}/download")
async def download_subject(
    assignment_id: int,
    db:            AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """Download the subject / problem statement file (students + professors)."""
    a = await get_assignment(db, assignment_id)

    if not a.assignment_file_path:
        raise HTTPException(
            status_code=404,
            detail="No subject file has been uploaded for this assignment",
        )

    p = Path(a.assignment_file_path)
    if not p.exists():
        raise HTTPException(
            status_code=404,
            detail="Subject file not found on disk — please re-upload it",
        )

    return FileResponse(str(p), filename=p.name)


# ════════════════════════════════════════════════════════════════
#  TEST CASE GENERATION
# ════════════════════════════════════════════════════════════════

@router.post("/{assignment_id}/generate-tests")
async def generate_tests(
    assignment_id: int,
    db:            AsyncSession = Depends(get_db),
    teacher=Depends(require_teacher),
):
    """
    Manually trigger test case generation from the reference solution.

    - Count is automatic: n × n based on detected input pattern
    - Score is always /20
    - Falls back to Claude API if execution fails
    - No desired_count parameter — fully automatic
    """
    a = await get_assignment(db, assignment_id)

    if not a.reference_solution_path:
        raise HTTPException(
            status_code=400,
            detail=(
                "No reference solution uploaded. "
                f"Upload one first via POST /assignments/{assignment_id}/reference-solution"
            ),
        )

    ref_path = Path(a.reference_solution_path)
    if not ref_path.exists():
        raise HTTPException(
            status_code=404,
            detail=(
                f"Reference solution file not found on disk: {ref_path}. "
                "Please re-upload the reference solution."
            ),
        )

    logger.info(
        "Manual test generation triggered for assignment %d (%s, %d bytes)",
        assignment_id, ref_path.name, ref_path.stat().st_size,
    )

    loop = asyncio.get_event_loop()

    # ── Step 1: compile check ─────────────────────────────────
    try:
        from app.services.execution_service import compile_c_file
        compile_result = await loop.run_in_executor(
            None, compile_c_file, ref_path
        )
        if not compile_result.success:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Reference solution does not compile:\n\n"
                    f"{compile_result.output}"
                ),
            )
        logger.info(
            "Reference solution compiles OK for assignment %d", assignment_id
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Compile check error: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Sandbox error during compile check: {exc}",
        )

    # ── Step 2: generate (count is automatic, score /20) ──────
    try:
        test_cases = await loop.run_in_executor(
            None,
            generate_test_cases,
            ref_path,
        )
    except Exception as exc:
        logger.error("Test generation exception: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Test generation failed: {exc}",
        )

    if not test_cases:
        raise HTTPException(
            status_code=422,
            detail=(
                "Could not generate test cases. "
                "The reference solution compiled but produced no usable output. "
                "Try uploading custom inputs via the alternative endpoint."
            ),
        )

    # ── Step 3: save ──────────────────────────────────────────
    a.test_cases = test_cases
    a.max_score  = 20.0
    await db.flush()
    await db.refresh(a)

    logger.info(
        "Generated %d test cases for assignment %d",
        len(test_cases), assignment_id,
    )

    return {
        "message":    f"Generated {len(test_cases)} test cases successfully",
        "count":      len(test_cases),
        "test_cases": test_cases,
    }


@router.post("/{assignment_id}/generate-tests-from-inputs")
async def generate_tests_from_custom_inputs(
    assignment_id: int,
    payload:       dict,
    db:            AsyncSession = Depends(get_db),
    teacher=Depends(require_teacher),
):
    """
    Generate test cases from teacher-provided stdin strings.

    Body: {"inputs": ["1 2", "0 0", "-5 3"], "merge": false}

    The system runs the reference solution for each input
    and captures the expected output automatically.
    merge=true appends to existing test cases instead of replacing.
    """
    inputs: list[str] = payload.get("inputs", [])

    if not inputs:
        raise HTTPException(
            status_code=400,
            detail="'inputs' list is required and cannot be empty",
        )
    if len(inputs) > 30:
        raise HTTPException(
            status_code=400,
            detail="Maximum 30 custom inputs allowed per request",
        )

    a = await get_assignment(db, assignment_id)

    if not a.reference_solution_path:
        raise HTTPException(
            status_code=400,
            detail="No reference solution uploaded",
        )

    ref_path = Path(a.reference_solution_path)
    if not ref_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Reference solution file not found on disk",
        )

    loop = asyncio.get_event_loop()

    try:
        test_cases = await loop.run_in_executor(
            None,
            generate_from_custom_inputs,
            ref_path,
            inputs,
        )
    except Exception as exc:
        logger.error("Custom input generation failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Generation failed: {exc}",
        )

    if not test_cases:
        raise HTTPException(
            status_code=422,
            detail=(
                "All custom inputs failed. "
                "Check that the reference solution handles these inputs correctly."
            ),
        )

    merge = payload.get("merge", False)
    if merge and a.test_cases:
        existing_ids = {tc["id"] for tc in a.test_cases}
        next_id      = max(existing_ids) + 1
        for tc in test_cases:
            tc["id"] = next_id
            next_id += 1
        a.test_cases = a.test_cases + test_cases
    else:
        a.test_cases = test_cases

    a.max_score = 20.0
    await db.flush()
    await db.refresh(a)

    return {
        "message":    f"Generated {len(test_cases)} test cases from custom inputs",
        "count":      len(test_cases),
        "test_cases": test_cases,
    }


# ════════════════════════════════════════════════════════════════
#  TEST CASE MANAGEMENT
# ════════════════════════════════════════════════════════════════

@router.get("/{assignment_id}/test-cases")
async def list_test_cases(
    assignment_id: int,
    db:            AsyncSession = Depends(get_db),
    teacher=Depends(require_teacher),
):
    """View all generated test cases for an assignment (professor only)."""
    a = await get_assignment(db, assignment_id)
    return {
        "assignment_id": assignment_id,
        "count":         len(a.test_cases or []),
        "test_cases":    a.test_cases or [],
    }


@router.put("/{assignment_id}/test-cases")
async def replace_test_cases(
    assignment_id: int,
    payload:       dict,
    db:            AsyncSession = Depends(get_db),
    teacher=Depends(require_teacher),
):
    """Manually replace all test cases with a custom list."""
    test_cases = payload.get("test_cases", [])
    if not isinstance(test_cases, list):
        raise HTTPException(
            status_code=400,
            detail="'test_cases' must be a list",
        )

    a            = await get_assignment(db, assignment_id)
    a.test_cases = test_cases
    a.max_score  = 20.0
    await db.flush()

    return {
        "message": f"Replaced with {len(test_cases)} test cases",
        "count":   len(test_cases),
    }


@router.delete("/{assignment_id}/test-cases")
async def clear_test_cases(
    assignment_id: int,
    db:            AsyncSession = Depends(get_db),
    teacher=Depends(require_teacher),
):
    """Clear all test cases for an assignment."""
    a            = await get_assignment(db, assignment_id)
    a.test_cases = []
    await db.flush()
    return {"message": "All test cases cleared"}


# ════════════════════════════════════════════════════════════════
#  STATIC ANALYSIS
# ════════════════════════════════════════════════════════════════

@router.post("/{assignment_id}/analyse-reference")
async def analyse_reference_solution(
    assignment_id: int,
    db:            AsyncSession = Depends(get_db),
    teacher=Depends(require_teacher),
):
    """
    Run static analysis on the uploaded reference solution.

    Returns:
    - Function names and signatures
    - Cyclomatic complexity
    - Control flow metrics (loops, recursion, gotos)
    - I/O patterns (scanf, printf, malloc, …)
    - Code quality warnings
    """
    a = await get_assignment(db, assignment_id)

    if not a.reference_solution_path:
        raise HTTPException(
            status_code=400,
            detail="No reference solution uploaded",
        )

    ref_path = Path(a.reference_solution_path)
    if not ref_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Reference solution file not found on disk",
        )

    loop   = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, analyse_c_file, ref_path)

    return analysis_to_dict(result)