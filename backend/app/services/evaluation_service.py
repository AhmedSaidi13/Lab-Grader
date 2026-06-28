"""
evaluation_service.py
─────────────────────
The evaluation brain of the grader.

Responsibilities:
  1. Normalize actual vs expected output for fair comparison
  2. Score each test case (pass/fail + partial credit)
  3. Apply compile bonus, late penalty, and score ceiling
  4. Produce a fully structured EvaluationReport (/20)
  5. Expose a single public entry point: evaluate_submission()

Scoring formula
───────────────
  raw_score  = Σ(passed_test_weight) / Σ(all_test_weights)  × max_score
  bonus      = compile_bonus_points  if compiled cleanly (no warnings)
  late_deduct= raw_score × late_penalty_percent / 100        if is_late
  final      = clamp(raw_score + bonus - late_deduct, 0, max_score)
"""

import re
import math
import logging
from dataclasses import dataclass, field
from typing import Optional

from app.services.execution_service import ExecutionResult, RunResult

logger = logging.getLogger(__name__)


# ── Normalisation settings ───────────────────────────────────────────────────

class NormMode:
    EXACT       = "exact"        # byte-for-byte match
    STRIP       = "strip"        # trim leading/trailing whitespace
    IGNORE_CASE = "ignore_case"  # case-insensitive + strip
    IGNORE_SPACE= "ignore_space" # collapse all whitespace
    NUMERIC     = "numeric"      # parse as numbers with tolerance
    REGEX       = "regex"        # expected_output is a regex pattern


DEFAULT_NORM_MODE = NormMode.STRIP
FLOAT_TOLERANCE   = 1e-6         # relative tolerance for numeric comparison


# ── Data structures ──────────────────────────────────────────────────────────

@dataclass
class TestCaseResult:
    test_id:          int
    description:      str
    passed:           bool
    partial_credit:   float        # 0.0 – 1.0
    points_earned:    float
    points_possible:  float
    input:            str
    expected_output:  str
    actual_output:    str
    execution_time_ms:float
    timed_out:        bool
    runtime_error:    bool
    stderr:           str
    norm_mode:        str
    diff_hint:        str          # short human-readable diff hint


@dataclass
class EvaluationReport:
    # Identity
    submission_id:     int
    assignment_id:     int
    student_id:        int

    # Compile
    compiled:          bool
    compile_output:    str
    compile_warnings:  list[str]   = field(default_factory=list)

    # Test results
    test_results:      list[TestCaseResult] = field(default_factory=list)

    # Score components
    raw_score:         float  = 0.0   # before bonus / penalty
    compile_bonus:     float  = 0.0
    late_penalty:      float  = 0.0
    final_score:       float  = 0.0   # clamped to [0, max_score]
    max_score:         float  = 20.0

    # Aggregates
    tests_total:       int    = 0
    tests_passed:      int    = 0
    tests_failed:      int    = 0
    tests_timeout:     int    = 0
    pass_rate:         float  = 0.0   # 0.0 – 1.0

    # Flags
    is_late:           bool   = False
    is_perfect:        bool   = False

    # Metadata
    grade_label:       str    = ""    # "Excellent", "Pass", "Fail", …


# ── Output normalisation ─────────────────────────────────────────────────────

def _normalise(text: str, mode: str) -> str:
    """Apply normalisation strategy to a string."""
    if mode == NormMode.EXACT:
        return text

    if mode == NormMode.STRIP:
        # Normalise line endings then strip each line
        lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        return "\n".join(line.rstrip() for line in lines).strip()

    if mode == NormMode.IGNORE_CASE:
        return _normalise(text, NormMode.STRIP).lower()

    if mode == NormMode.IGNORE_SPACE:
        return re.sub(r"\s+", " ", text).strip().lower()

    if mode == NormMode.NUMERIC:
        # Extract all numbers and compare as floats
        return text   # handled separately in _compare

    if mode == NormMode.REGEX:
        return text   # pattern match handled in _compare

    return text.strip()


def _extract_numbers(text: str) -> list[float]:
    """Extract all numeric tokens from a string."""
    tokens = re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", text)
    result = []
    for t in tokens:
        try:
            result.append(float(t))
        except ValueError:
            pass
    return result


def _compare(
    actual: str,
    expected: str,
    mode: str,
) -> tuple[bool, str]:
    """
    Compare actual vs expected output using the given normalisation mode.
    Returns (passed, diff_hint).
    """
    # ── Regex mode ──────────────────────────────────────────────
    if mode == NormMode.REGEX:
        try:
            matched = bool(re.fullmatch(expected.strip(), actual.strip(), re.DOTALL))
            hint = "" if matched else f"Output did not match pattern: {expected[:80]}"
            return matched, hint
        except re.error as exc:
            return False, f"Invalid regex in expected output: {exc}"

    # ── Numeric mode ────────────────────────────────────────────
    if mode == NormMode.NUMERIC:
        actual_nums   = _extract_numbers(actual)
        expected_nums = _extract_numbers(expected)
        if len(actual_nums) != len(expected_nums):
            hint = (
                f"Expected {len(expected_nums)} number(s), "
                f"got {len(actual_nums)}"
            )
            return False, hint
        for a_val, e_val in zip(actual_nums, expected_nums):
            if e_val == 0:
                ok = abs(a_val) < FLOAT_TOLERANCE
            else:
                ok = math.isclose(a_val, e_val, rel_tol=FLOAT_TOLERANCE)
            if not ok:
                return False, f"Numeric mismatch: expected {e_val}, got {a_val}"
        return True, ""

    # ── Text modes ───────────────────────────────────────────────
    norm_actual   = _normalise(actual,   mode)
    norm_expected = _normalise(expected, mode)

    if norm_actual == norm_expected:
        return True, ""

    # Build a concise diff hint
    hint = _build_diff_hint(norm_actual, norm_expected)
    return False, hint


def _build_diff_hint(actual: str, expected: str) -> str:
    """
    Produce a short, human-readable diff hint without importing difflib
    for heavy output. Keeps the hint under 200 chars.
    """
    actual_lines   = actual.split("\n")
    expected_lines = expected.split("\n")

    if len(actual_lines) != len(expected_lines):
        return (
            f"Line count mismatch: expected {len(expected_lines)} line(s), "
            f"got {len(actual_lines)}"
        )

    for i, (a_line, e_line) in enumerate(zip(actual_lines, expected_lines)):
        if a_line != e_line:
            hint = f"Line {i+1}: expected '{e_line[:60]}', got '{a_line[:60]}'"
            return hint[:200]

    return "Outputs differ (trailing content or encoding issue)"


# ── Compile warning extraction ───────────────────────────────────────────────

def _extract_warnings(compile_output: str) -> list[str]:
    """Parse GCC output and return warning lines."""
    warnings = []
    for line in compile_output.splitlines():
        if ": warning:" in line or "[-W" in line:
            warnings.append(line.strip())
    return warnings


# ── Per-test scoring ─────────────────────────────────────────────────────────

def _score_test(
    tc: dict,
    run: RunResult,
) -> TestCaseResult:
    """
    Score a single test case.

    Partial credit rules:
      - Full timeout          → 0.0
      - Runtime error (!=0)   → 0.0  (unless partial_credit_on_error = True in tc)
      - Pass                  → 1.0
      - Fail                  → 0.0  (binary by default)
                                partial credit fraction if tc has "partial_credit_threshold"
    """
    test_id       = tc.get("id", 0)
    description   = tc.get("description", f"Test {test_id}")
    weight        = float(tc.get("weight", 1.0))
    norm_mode     = tc.get("norm_mode", DEFAULT_NORM_MODE)
    expected      = str(tc.get("expected_output", "")).strip()

    actual        = run.stdout.strip() if run else ""
    timed_out     = run.timed_out     if run else False
    runtime_error = (run.exit_code != 0 and not timed_out) if run else False
    stderr        = run.stderr        if run else ""
    exec_time_ms  = run.duration_ms   if run else 0.0

    # Hard failures — no partial credit
    if timed_out:
        return TestCaseResult(
            test_id=test_id, description=description,
            passed=False, partial_credit=0.0,
            points_earned=0.0, points_possible=weight,
            input=tc.get("input", ""), expected_output=expected,
            actual_output=actual, execution_time_ms=exec_time_ms,
            timed_out=True, runtime_error=False, stderr=stderr,
            norm_mode=norm_mode,
            diff_hint="Program exceeded time limit",
        )

    if runtime_error and not tc.get("partial_credit_on_error", False):
        return TestCaseResult(
            test_id=test_id, description=description,
            passed=False, partial_credit=0.0,
            points_earned=0.0, points_possible=weight,
            input=tc.get("input", ""), expected_output=expected,
            actual_output=actual, execution_time_ms=exec_time_ms,
            timed_out=False, runtime_error=True, stderr=stderr,
            norm_mode=norm_mode,
            diff_hint=f"Program exited with code {run.exit_code}",
        )

    # Output comparison
    passed, diff_hint = _compare(actual, expected, norm_mode)

    if passed:
        return TestCaseResult(
            test_id=test_id, description=description,
            passed=True, partial_credit=1.0,
            points_earned=weight, points_possible=weight,
            input=tc.get("input", ""), expected_output=expected,
            actual_output=actual, execution_time_ms=exec_time_ms,
            timed_out=False, runtime_error=False, stderr=stderr,
            norm_mode=norm_mode, diff_hint="",
        )

    # Optional partial credit for close answers
    partial = 0.0
    threshold = tc.get("partial_credit_threshold")
    if threshold is not None:
        # Give half marks if output contains the expected string
        if expected and expected in actual:
            partial = 0.5

    return TestCaseResult(
        test_id=test_id, description=description,
        passed=False, partial_credit=partial,
        points_earned=round(weight * partial, 4),
        points_possible=weight,
        input=tc.get("input", ""), expected_output=expected,
        actual_output=actual, execution_time_ms=exec_time_ms,
        timed_out=False, runtime_error=runtime_error, stderr=stderr,
        norm_mode=norm_mode, diff_hint=diff_hint,
    )


# ── Grade label ──────────────────────────────────────────────────────────────

def _grade_label(score: float, max_score: float, passing: float) -> str:
    ratio = score / max_score if max_score > 0 else 0
    if score >= max_score:
        return "Perfect"
    if ratio >= 0.90:
        return "Excellent"
    if ratio >= 0.75:
        return "Good"
    if score >= passing:
        return "Pass"
    if ratio >= 0.40:
        return "Needs Work"
    return "Fail"


# ── Main public entry point ──────────────────────────────────────────────────

def evaluate_submission(
    submission_id:       int,
    assignment_id:       int,
    student_id:          int,
    exec_result:         ExecutionResult,
    test_cases:          list[dict],
    max_score:           float = 20.0,
    passing_score:       float = 10.0,
    is_late:             bool  = False,
    late_penalty_pct:    float = 0.0,
    compile_bonus_pts:   float = 0.0,   # bonus for zero warnings
) -> EvaluationReport:
    """
    Master evaluation function.

    Parameters
    ──────────
    exec_result        ExecutionResult from execution_service
    test_cases         list of test case dicts (from Assignment.test_cases)
    max_score          ceiling score (default 20)
    passing_score      minimum passing score (default 10)
    is_late            flag for late submission
    late_penalty_pct   percentage deducted for late (e.g. 20 → -20%)
    compile_bonus_pts  extra points if compiled with zero warnings

    Returns
    ───────
    EvaluationReport   fully populated dataclass
    """
    report = EvaluationReport(
        submission_id=submission_id,
        assignment_id=assignment_id,
        student_id=student_id,
        compiled=exec_result.compile.success,
        compile_output=exec_result.compile.output,
        max_score=max_score,
        is_late=is_late,
    )

    # ── Did not compile ──────────────────────────────────────────
    if not exec_result.compile.success:
        report.raw_score    = 0.0
        report.final_score  = 0.0
        report.tests_total  = len(test_cases)
        report.grade_label  = "Fail"
        return report

    # ── Extract compile warnings ─────────────────────────────────
    report.compile_warnings = _extract_warnings(exec_result.compile.output)

    # Apply compile bonus only if zero warnings
    if compile_bonus_pts > 0 and len(report.compile_warnings) == 0:
        report.compile_bonus = compile_bonus_pts

    # ── No test cases — full score for compiling ─────────────────
    if not test_cases:
        report.raw_score   = max_score
        report.final_score = min(max_score + report.compile_bonus, max_score)
        report.grade_label = _grade_label(report.final_score, max_score, passing_score)
        return report

    # ── Score each test case ─────────────────────────────────────
    runs = exec_result.runs   # parallel list with test_cases

    tc_results: list[TestCaseResult] = []
    for i, tc in enumerate(test_cases):
        run = runs[i] if i < len(runs) else None
        tc_result = _score_test(tc, run)
        tc_results.append(tc_result)

    report.test_results = tc_results

    # ── Aggregate counts ─────────────────────────────────────────
    report.tests_total   = len(tc_results)
    report.tests_passed  = sum(1 for r in tc_results if r.passed)
    report.tests_failed  = sum(1 for r in tc_results if not r.passed and not r.timed_out)
    report.tests_timeout = sum(1 for r in tc_results if r.timed_out)
    report.pass_rate     = (
        report.tests_passed / report.tests_total
        if report.tests_total > 0 else 0.0
    )

    # ── Raw score ────────────────────────────────────────────────
    total_weight  = sum(r.points_possible for r in tc_results)
    earned_weight = sum(r.points_earned   for r in tc_results)

    if total_weight > 0:
        report.raw_score = round((earned_weight / total_weight) * max_score, 4)
    else:
        report.raw_score = 0.0

    # ── Apply compile bonus ──────────────────────────────────────
    score_with_bonus = report.raw_score + report.compile_bonus

    # ── Apply late penalty ───────────────────────────────────────
    if is_late and late_penalty_pct > 0:
        report.late_penalty = round(
            report.raw_score * (late_penalty_pct / 100), 4
        )

    # ── Final score (clamped) ─────────────────────────────────────
    report.final_score = round(
        max(0.0, min(max_score, score_with_bonus - report.late_penalty)),
        2,
    )

    # ── Flags & label ────────────────────────────────────────────
    report.is_perfect  = report.final_score >= max_score
    report.grade_label = _grade_label(report.final_score, max_score, passing_score)

    logger.info(
        "Evaluated submission %d: %.2f/%s [%s] (passed %d/%d tests)",
        submission_id, report.final_score, max_score,
        report.grade_label, report.tests_passed, report.tests_total,
    )

    return report


# ── Score breakdown serialiser ───────────────────────────────────────────────

def report_to_dict(report: EvaluationReport) -> dict:
    """
    Convert an EvaluationReport to a JSON-serialisable dict.
    Stored in Submission.test_results and returned via the API.
    """
    return {
        "submission_id":    report.submission_id,
        "assignment_id":    report.assignment_id,
        "student_id":       report.student_id,
        "compiled":         report.compiled,
        "compile_output":   report.compile_output,
        "compile_warnings": report.compile_warnings,
        "score": {
            "raw":          report.raw_score,
            "compile_bonus":report.compile_bonus,
            "late_penalty": report.late_penalty,
            "final":        report.final_score,
            "max":          report.max_score,
            "label":        report.grade_label,
        },
        "tests": {
            "total":         report.tests_total,
            "passed":        report.tests_passed,
            "failed":        report.tests_failed,
            "timed_out":     report.tests_timeout,
            "pass_rate_pct": round(report.pass_rate * 100, 1),
        },
        "is_late":     report.is_late,
        "is_perfect":  report.is_perfect,
        "test_results": [
            {
                "test_id":          r.test_id,
                "description":      r.description,
                "passed":           r.passed,
                "partial_credit":   r.partial_credit,
                "points_earned":    r.points_earned,
                "points_possible":  r.points_possible,
                "input":            r.input,
                "expected_output":  r.expected_output,
                "actual_output":    r.actual_output,
                "execution_time_ms":round(r.execution_time_ms, 1),
                "timed_out":        r.timed_out,
                "runtime_error":    r.runtime_error,
                "stderr":           r.stderr,
                "norm_mode":        r.norm_mode,
                "diff_hint":        r.diff_hint,
            }
            for r in report.test_results
        ],
    }

