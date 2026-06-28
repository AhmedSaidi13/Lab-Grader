import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from celery import Task
from celery.exceptions import SoftTimeLimitExceeded
from celery.utils.log import get_task_logger

from app.workers.celery_app import celery_app
from app.config import get_settings

settings = get_settings()
logger   = get_task_logger(__name__)

import redis as redis_lib
_redis_client = redis_lib.from_url(settings.REDIS_URL, decode_responses=True)

PROGRESS_TTL = 3600


# ── Progress helpers ──────────────────────────────────────────

def _set_progress(task_id: str, step: str, percent: int, message: str) -> None:
    try:
        _redis_client.setex(
            f"task:progress:{task_id}",
            PROGRESS_TTL,
            json.dumps({
                "task_id": task_id,
                "step":    step,
                "percent": percent,
                "message": message,
                "ts":      datetime.now(timezone.utc).isoformat(),
            }),
        )
    except Exception as exc:
        logger.warning("Progress write failed: %s", exc)


def get_task_progress(task_id: str) -> Optional[dict]:
    try:
        raw = _redis_client.get(f"task:progress:{task_id}")
        return json.loads(raw) if raw else None
    except Exception:
        return None


# ── DB session ────────────────────────────────────────────────

def _get_sync_session():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    engine  = create_engine(
        settings.SYNC_DATABASE_URL,
        pool_size    = 5,
        max_overflow = 10,
        pool_pre_ping= True,
    )
    return sessionmaker(bind=engine)()


# ── Base task ─────────────────────────────────────────────────

class BaseGraderTask(Task):
    abstract = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error("Task %s [%s] failed: %s", self.name, task_id, exc)
        _set_progress(task_id, "failed", 0, f"Failed: {exc}")

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        logger.warning("Task %s [%s] retrying: %s", self.name, task_id, exc)

    def on_success(self, retval, task_id, args, kwargs):
        logger.info("Task %s [%s] succeeded.", self.name, task_id)


# ── Task 1: evaluate_submission_task ──────────────────────────

@celery_app.task(
    bind=True,
    base=BaseGraderTask,
    name="app.workers.tasks.evaluate_submission_task",
    max_retries=3,
    default_retry_delay=10,
)
def evaluate_submission_task(self, submission_id: int) -> dict:
    task_id = self.request.id
    db      = _get_sync_session()

    try:
        _set_progress(task_id, "starting", 5, "Fetching submission…")

        from app.models.submission import Submission, SubmissionStatus
        from app.models.assignment import Assignment
        from app.models.user       import User

        sub = db.query(Submission).filter(Submission.id == submission_id).first()
        if not sub:
            raise ValueError(f"Submission {submission_id} not found")

        assignment = db.query(Assignment).filter(
            Assignment.id == sub.assignment_id
        ).first()
        if not assignment:
            raise ValueError(f"Assignment {sub.assignment_id} not found")

        student = db.query(User).filter(User.id == sub.student_id).first()
        test_cases = assignment.test_cases or []

        _set_progress(task_id, "validating", 10, "Validating source file…")

        source_path = Path(sub.file_path)
        if not source_path.exists():
            sub.status         = SubmissionStatus.failed
            sub.compile_output = "Source file missing from disk"
            sub.evaluated_at   = datetime.now(timezone.utc)
            db.commit()
            return {"status": "failed", "reason": "file_missing"}

        sub.status         = SubmissionStatus.compiling
        sub.celery_task_id = task_id
        db.commit()

        _set_progress(task_id, "compiling", 25, "Compiling your C code…")

        from app.services.execution_service import run_c_file_with_tests
        exec_result = run_c_file_with_tests(source_path, test_cases)

        sub.compile_output = exec_result.compile.output

        if not exec_result.compile.success:
            sub.status       = SubmissionStatus.compile_error
            sub.score        = 0.0
            sub.evaluated_at = datetime.now(timezone.utc)
            sub.feedback     = json.dumps({
                "summary":  "Your code did not compile.",
                "sections": [{
                    "title": "Compile Error",
                    "body":  f"```\n{exec_result.compile.output}\n```",
                    "level": "error",
                    "code":  None,
                }],
                "generated_by_llm": False,
            })
            db.commit()
            _set_progress(task_id, "done", 100, "Compile error")

            # Notify student
            _notify_student_sync(
                db         = db,
                student_id = sub.student_id,
                sub        = sub,
                assignment = assignment,
                score      = 0.0,
                grade      = "Compile Error",
            )
            return {"status": "compile_error", "submission_id": submission_id, "score": 0.0}

        _set_progress(task_id, "running", 55,
                      f"Running {len(test_cases)} test cases…")
        sub.status = SubmissionStatus.running
        db.commit()

        _set_progress(task_id, "evaluating", 70, "Scoring results…")
        sub.status = SubmissionStatus.evaluating
        db.commit()

        from app.services.evaluation_service import evaluate_submission, report_to_dict
        report = evaluate_submission(
            submission_id    = sub.id,
            assignment_id    = sub.assignment_id,
            student_id       = sub.student_id,
            exec_result      = exec_result,
            test_cases       = test_cases,
            max_score        = 20.0,          # always /20
            passing_score    = assignment.passing_score,
            is_late          = sub.is_late,
            late_penalty_pct = assignment.late_penalty_percent or 0.0,
        )
        full_report = report_to_dict(report)

        _set_progress(task_id, "analysis", 85, "Running static analysis…")

        from app.services.static_analysis import analyse_c_file, analysis_to_dict
        sa_result = analyse_c_file(source_path)

        _set_progress(task_id, "feedback", 92, "Generating feedback…")

        from app.services.feedback_service import (
            generate_feedback, feedback_report_to_dict
        )
        feedback_report = generate_feedback(
            submission_id   = sub.id,
            score           = report.final_score,
            max_score       = 20.0,
            grade_label     = report.grade_label,
            compile_output  = exec_result.compile.output,
            test_results    = full_report["test_results"],
            static_analysis = analysis_to_dict(sa_result),
            is_late         = sub.is_late,
            late_penalty    = report.late_penalty,
            source_path     = source_path,
            use_llm         = settings.USE_LLM_FEEDBACK,
        )

        _set_progress(task_id, "saving", 95, "Saving results…")

        sub.score           = report.final_score
        sub.test_results    = full_report["test_results"]
        sub.static_analysis = analysis_to_dict(sa_result)
        sub.feedback        = json.dumps(feedback_report_to_dict(feedback_report))
        sub.status          = SubmissionStatus.completed
        sub.evaluated_at    = datetime.now(timezone.utc)
        db.commit()
        db.refresh(sub)

        _set_progress(
            task_id, "completed", 100,
            f"Done — {report.final_score}/20 ({report.grade_label})",
        )

        # ── Notify student ────────────────────────────────────
        _notify_student_sync(
            db         = db,
            student_id = sub.student_id,
            sub        = sub,
            assignment = assignment,
            score      = report.final_score,
            grade      = report.grade_label,
        )

        logger.info(
            "Evaluated submission %d → %.2f/20", submission_id, report.final_score
        )

        return {
            "status":        "completed",
            "submission_id": submission_id,
            "score":         report.final_score,
            "grade_label":   report.grade_label,
            "tests_passed":  report.tests_passed,
            "tests_total":   report.tests_total,
        }

    except SoftTimeLimitExceeded:
        logger.error("Submission %d timed out", submission_id)
        try:
            from app.models.submission import Submission, SubmissionStatus
            sub = db.query(Submission).filter(Submission.id == submission_id).first()
            if sub:
                sub.status   = SubmissionStatus.timeout
                sub.feedback = json.dumps({
                    "summary":  "Evaluation timed out.",
                    "sections": [{
                        "title": "Timeout",
                        "body":  "Evaluation exceeded the time limit. "
                                 "Check for infinite loops.",
                        "level": "error",
                        "code":  None,
                    }],
                    "generated_by_llm": False,
                })
                db.commit()
        except Exception:
            pass
        _set_progress(task_id, "timeout", 0, "Evaluation timed out")
        return {"status": "timeout", "submission_id": submission_id}

    except Exception as exc:
        logger.error(
            "Evaluation failed for submission %d: %s",
            submission_id, exc, exc_info=True,
        )
        try:
            from app.models.submission import Submission, SubmissionStatus
            sub = db.query(Submission).filter(Submission.id == submission_id).first()
            if sub:
                sub.status   = SubmissionStatus.failed
                sub.feedback = json.dumps({
                    "summary":  f"Internal error: {exc}",
                    "sections": [],
                    "generated_by_llm": False,
                })
                db.commit()
        except Exception:
            pass
        raise self.retry(exc=exc, countdown=2 ** self.request.retries * 10)

    finally:
        db.close()


# ── Notification helper (sync, for Celery) ────────────────────

def _notify_student_sync(db, student_id, sub, assignment, score, grade) -> None:
    """Create a notification for the student after evaluation."""
    try:
        from app.models.notification import Notification, NotificationType

        emoji = (
            "🏆" if grade == "Perfect"    else
            "🌟" if grade == "Excellent"  else
            "👍" if grade == "Good"       else
            "✅" if grade == "Pass"       else
            "⚠️" if grade == "Needs Work" else
            "❌"
        )

        title   = f"{emoji} {assignment.title} — Corrected"
        message = (
            f"Your submission for '{assignment.title}' has been evaluated.\n"
            f"Score: {score}/20 ({grade})"
        )
        if sub.is_late:
            message += "\n⏰ Late submission penalty was applied."

        notif = Notification(
            user_id = student_id,
            type    = NotificationType.evaluation_complete,
            title   = title,
            message = message,
            link    = f"/submissions/{sub.id}",
            is_read = False,
        )
        db.add(notif)
        db.commit()
        logger.info(
            "Notification sent to student %d for submission %d",
            student_id, sub.id,
        )
    except Exception as exc:
        logger.error("Failed to create notification: %s", exc)


# ── Task 2: generate_tests_task ───────────────────────────────

@celery_app.task(
    bind=True,
    base=BaseGraderTask,
    name="app.workers.tasks.generate_tests_task",
    max_retries=2,
    default_retry_delay=15,
)
def generate_tests_task(self, assignment_id: int) -> dict:
    task_id = self.request.id
    db      = _get_sync_session()

    try:
        _set_progress(task_id, "loading", 10, "Loading assignment…")

        from app.models.assignment import Assignment
        assignment = db.query(Assignment).filter(
            Assignment.id == assignment_id
        ).first()
        if not assignment:
            raise ValueError(f"Assignment {assignment_id} not found")
        if not assignment.reference_solution_path:
            raise ValueError("No reference solution uploaded")

        ref_path = Path(assignment.reference_solution_path)
        if not ref_path.exists():
            raise ValueError(f"Reference file not found: {ref_path}")

        _set_progress(task_id, "generating", 40, "Running reference solution…")

        from app.services.test_generator import generate_test_cases
        test_cases = generate_test_cases(ref_path)

        _set_progress(task_id, "saving", 90,
                      f"Saving {len(test_cases)} test cases…")

        assignment.test_cases = test_cases
        assignment.max_score  = 20.0
        db.commit()

        _set_progress(
            task_id, "completed", 100,
            f"Generated {len(test_cases)} test cases (/20)",
        )

        return {
            "status":        "completed",
            "assignment_id": assignment_id,
            "count":         len(test_cases),
        }

    except Exception as exc:
        logger.error(
            "Test generation failed for assignment %d: %s",
            assignment_id, exc,
        )
        raise self.retry(exc=exc, countdown=2 ** self.request.retries * 15)

    finally:
        db.close()


# ── Task 3: evaluate_expired_assignments ─────────────────────

@celery_app.task(
    name="app.workers.tasks.evaluate_expired_assignments",
    queue="maintenance",
)
def evaluate_expired_assignments() -> dict:
    """
    Runs every 2 minutes (beat schedule).
    Finds assignments whose deadline just passed and
    dispatches evaluation for all pending submissions.
    Also sends a deadline-passed notification to students
    who never submitted.
    """
    db = _get_sync_session()
    dispatched_total = 0
    notified_total   = 0

    try:
        from app.models.assignment import Assignment
        from app.models.submission import Submission, SubmissionStatus
        from app.models.user       import User, UserRole
        from app.models.notification import Notification, NotificationType

        now = datetime.now(timezone.utc)

        # Assignments that expired in the last 4 minutes
        # (2-min beat interval + 2-min buffer for overlap)
        window_start = now - timedelta(minutes=4)

        expired = (
            db.query(Assignment)
            .filter(
                Assignment.deadline    != None,       # noqa
                Assignment.deadline    <= now,
                Assignment.deadline    >= window_start,
                Assignment.is_published == True,      # noqa
            )
            .all()
        )

        logger.info(
            "Deadline check: found %d assignment(s) that just expired",
            len(expired),
        )

        for assignment in expired:
            # Find all pending/queued submissions
            pending_subs = (
                db.query(Submission)
                .filter(
                    Submission.assignment_id == assignment.id,
                    Submission.status.in_([
                        SubmissionStatus.pending,
                        SubmissionStatus.queued,
                        SubmissionStatus.failed,
                    ]),
                )
                .all()
            )

            for sub in pending_subs:
                # Reset to pending and dispatch evaluation
                sub.status = SubmissionStatus.queued
                db.commit()

                evaluate_submission_task.apply_async(
                    args  = [sub.id],
                    queue = "evaluation",
                )
                dispatched_total += 1
                logger.info(
                    "Dispatched evaluation for submission %d "
                    "(assignment %d expired)",
                    sub.id, assignment.id,
                )

            # Notify students who submitted but aren't evaluated yet
            # (already queued above)

            # Find students who NEVER submitted
            all_students = (
                db.query(User)
                .filter(User.role == UserRole.student, User.is_active == True)  # noqa
                .all()
            )
            submitted_student_ids = set(
                db.query(Submission.student_id)
                .filter(Submission.assignment_id == assignment.id)
                .distinct()
                .all()
            )
            submitted_ids = {r[0] for r in submitted_student_ids}

            for student in all_students:
                if student.id not in submitted_ids:
                    # Check if we already notified this student for this assignment
                    existing = (
                        db.query(Notification)
                        .filter(
                            Notification.user_id == student.id,
                            Notification.type    == NotificationType.deadline_passed,
                            Notification.link    == f"/assignments/{assignment.id}",
                        )
                        .first()
                    )
                    if not existing:
                        notif = Notification(
                            user_id = student.id,
                            type    = NotificationType.deadline_passed,
                            title   = f"⏰ Deadline passed — {assignment.title}",
                            message = (
                                f"The deadline for '{assignment.title}' has passed. "
                                "You did not submit a solution."
                            ),
                            link    = f"/assignments/{assignment.id}",
                        )
                        db.add(notif)
                        notified_total += 1

            db.commit()

        logger.info(
            "Deadline check done: dispatched=%d, missed-notified=%d",
            dispatched_total, notified_total,
        )
        return {
            "assignments_processed": len(expired),
            "dispatched":            dispatched_total,
            "notified_missed":       notified_total,
        }

    except Exception as exc:
        logger.error("evaluate_expired_assignments failed: %s", exc, exc_info=True)
        return {"error": str(exc)}

    finally:
        db.close()


# ── Task 4: bulk_reevaluate_task ──────────────────────────────

@celery_app.task(
    bind=True,
    base=BaseGraderTask,
    name="app.workers.tasks.bulk_reevaluate_task",
    max_retries=1,
)
def bulk_reevaluate_task(self, assignment_id: int) -> dict:
    task_id = self.request.id
    db      = _get_sync_session()

    try:
        _set_progress(task_id, "loading", 5, "Loading submissions…")

        from app.models.submission import Submission, SubmissionStatus
        submissions = (
            db.query(Submission)
            .filter(
                Submission.assignment_id == assignment_id,
                Submission.status.in_([
                    SubmissionStatus.completed,
                    SubmissionStatus.compile_error,
                    SubmissionStatus.failed,
                    SubmissionStatus.timeout,
                ]),
            )
            .all()
        )

        total = len(submissions)
        if total == 0:
            _set_progress(task_id, "completed", 100, "No submissions to re-evaluate")
            return {"status": "completed", "dispatched": 0}

        _set_progress(task_id, "dispatching", 20,
                      f"Dispatching {total} evaluation tasks…")

        for i, sub in enumerate(submissions):
            sub.status         = SubmissionStatus.pending
            sub.score          = None
            sub.test_results   = []
            sub.static_analysis= {}
            sub.feedback       = None
            sub.evaluated_at   = None
            db.commit()

            evaluate_submission_task.apply_async(
                args  = [sub.id],
                queue = "evaluation",
            )

            _set_progress(
                task_id, "dispatching",
                20 + int((i + 1) / total * 70),
                f"Dispatched {i+1}/{total}…",
            )

        _set_progress(task_id, "completed", 100,
                      f"Dispatched {total} re-evaluations")

        return {
            "status":        "completed",
            "assignment_id": assignment_id,
            "dispatched":    total,
        }

    except Exception as exc:
        logger.error("Bulk re-evaluation failed: %s", exc, exc_info=True)
        raise self.retry(exc=exc, countdown=30)

    finally:
        db.close()


# ── Task 5: cleanup_old_tasks (beat 3 AM) ────────────────────

@celery_app.task(
    name="app.workers.tasks.cleanup_old_tasks",
    queue="maintenance",
)
def cleanup_old_tasks() -> dict:
    db      = _get_sync_session()
    cleaned = 0
    try:
        from app.models.submission import Submission, SubmissionStatus
        cutoff = datetime.now(timezone.utc) - timedelta(hours=2)
        stale  = (
            db.query(Submission)
            .filter(
                Submission.status.in_([
                    SubmissionStatus.queued,
                    SubmissionStatus.compiling,
                    SubmissionStatus.running,
                    SubmissionStatus.evaluating,
                ]),
                Submission.submitted_at < cutoff,
            )
            .all()
        )
        for sub in stale:
            sub.status   = SubmissionStatus.failed
            sub.feedback = json.dumps({
                "summary":  "Evaluation timed out and was reset.",
                "sections": [],
                "generated_by_llm": False,
            })
            cleaned += 1
        db.commit()
        logger.info("Cleanup: reset %d stale submissions", cleaned)
        return {"cleaned_submissions": cleaned}
    except Exception as exc:
        logger.error("Cleanup failed: %s", exc)
        return {"error": str(exc)}
    finally:
        db.close()