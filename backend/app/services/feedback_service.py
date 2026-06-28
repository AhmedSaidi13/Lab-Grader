"""
feedback_service.py
───────────────────
Multi-layer automatic feedback generator.

Layer 1 — Rule-Based (always runs, zero latency)
  Analyses evaluation report + static analysis results and
  produces structured, deterministic feedback covering:
    • Compile errors   → parse GCC output, map to actionable hints
    • Failed tests     → per-test explanation + diff analysis
    • Timeout          → infinite loop / complexity hints
    • Static analysis  → code quality warnings with fix suggestions
    • Score summary    → motivational + diagnostic summary

Layer 2 — LLM-Powered (optional, runs if ANTHROPIC_API_KEY is set)
  Sends a carefully structured prompt to claude-haiku-4-5 with:
    • The student's source code
    • All failed test cases + actual outputs
    • Static analysis metrics
  Returns rich natural-language suggestions and code hints.
  Falls back gracefully to Layer 1 if the API is unavailable.

Output
──────
  FeedbackReport dataclass → stored as JSON in Submission.feedback
  Also returned as plain text summary for backwards compatibility.
"""

import re
import os
import json
import logging
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


# ── Data structures ───────────────────────────────────────────────────────────

@dataclass
class FeedbackSection:
    title:   str
    body:    str
    level:   str = "info"    # "info" | "warning" | "error" | "success" | "tip"
    code:    Optional[str] = None   # optional code snippet hint


@dataclass
class FeedbackReport:
    # Identity
    submission_id:  int
    grade_label:    str
    score:          float
    max_score:      float
    pass_rate:      float        # 0.0 – 1.0

    # Sections (ordered for display)
    sections:       list[FeedbackSection] = field(default_factory=list)

    # Quick summary (plain text, for backwards-compat)
    summary:        str = ""

    # Flags
    generated_by_llm: bool = False
    llm_error:        Optional[str] = None


# ── GCC error parser ──────────────────────────────────────────────────────────

# Maps common GCC error substrings → plain-English hints
_GCC_HINTS: list[tuple[str, str]] = [
    ("expected ';'",
     "You are missing a semicolon. Every statement in C must end with ';'."),
    ("expected ')'",
     "A closing parenthesis ')' is missing. Check your function calls and expressions."),
    ("expected '}'",
     "A closing brace '}' is missing. Every '{' must have a matching '}'."),
    ("undeclared",
     "You are using a variable or function that was never declared. "
     "Make sure to declare all variables at the top of the function and "
     "#include the right headers."),
    ("implicit declaration of function",
     "A function is called before it is declared. Add a prototype at the top "
     "or #include the correct header (e.g. #include <stdio.h> for printf/scanf)."),
    ("incompatible types",
     "You are assigning a value of the wrong type. Check that your variable "
     "types match (int, float, char, etc.)."),
    ("too few arguments",
     "A function call is missing arguments. Check the function signature."),
    ("too many arguments",
     "A function call has more arguments than the function accepts."),
    ("lvalue required",
     "You are trying to assign a value to something that cannot be assigned to. "
     "Check the left side of your '=' operator."),
    ("subscripted value is neither array nor pointer",
     "You are using [] on a variable that is not an array. "
     "Check your variable declarations."),
    ("return type",
     "The return type of your function does not match what you declared. "
     "If your function is 'int', make sure you return an int value."),
    ("control reaches end",
     "Not all code paths return a value. Add a return statement at the end."),
    ("format '%d' expects",
     "printf/scanf format mismatch: you used %d but the variable is not an int. "
     "Use %f for float, %lf for double, %s for string, %c for char."),
    ("format '%f' expects",
     "printf/scanf format mismatch: you used %f but the variable is not a float. "
     "Use %d for int, %s for string, %c for char."),
    ("unused variable",
     "A variable is declared but never used. Either use it or remove the declaration."),
    ("division by zero",
     "Potential division by zero detected. Add a check before dividing."),
    ("pointer",
     "Pointer issue detected. Make sure you dereference pointers with * "
     "and that you initialise them before use."),
]


def _parse_gcc_errors(compile_output: str) -> list[FeedbackSection]:
    """Parse GCC output and return actionable FeedbackSections."""
    sections: list[FeedbackSection] = []
    if not compile_output or "Compilation successful" in compile_output:
        return sections

    lines = compile_output.splitlines()
    error_lines   = [l for l in lines if ": error:"   in l]
    warning_lines = [l for l in lines if ": warning:" in l]

    # Per-error sections
    seen_hints: set[str] = set()
    for err_line in error_lines[:5]:   # cap at 5 to avoid wall of text
        # Extract file:line:col: error: message
        m = re.search(r':(\d+):\d+:\s+error:\s+(.+)', err_line)
        if not m:
            continue
        lineno = m.group(1)
        errmsg = m.group(2).strip()

        # Find matching hint
        hint = ""
        for pattern, suggestion in _GCC_HINTS:
            if pattern.lower() in errmsg.lower() and suggestion not in seen_hints:
                hint = suggestion
                seen_hints.add(suggestion)
                break

        body = f"**Line {lineno}**: `{errmsg}`"
        if hint:
            body += f"\n\n💡 {hint}"

        sections.append(FeedbackSection(
            title=f"Compile Error — Line {lineno}",
            body=body,
            level="error",
        ))

    # Warning summary
    if warning_lines:
        w_text = "\n".join(f"• {l.split(': warning:')[-1].strip()}"
                           for l in warning_lines[:4])
        sections.append(FeedbackSection(
            title=f"{len(warning_lines)} Compiler Warning(s)",
            body=(
                "Your code compiled with warnings. While warnings do not prevent "
                "compilation, they often indicate bugs:\n\n" + w_text
            ),
            level="warning",
        ))

    return sections


# ── Per-test feedback ─────────────────────────────────────────────────────────

def _feedback_for_failed_test(result: dict) -> FeedbackSection:
    """Produce a FeedbackSection for one failing test case."""
    tid   = result.get("test_id", "?")
    desc  = result.get("description", f"Test {tid}")
    inp   = result.get("input",           "")
    exp   = result.get("expected_output", "")
    act   = result.get("actual_output",   "")
    hint  = result.get("diff_hint",       "")
    tout  = result.get("timed_out",       False)
    rerr  = result.get("runtime_error",   False)
    ec    = result.get("exit_code",       0)

    lines: list[str] = []

    if tout:
        lines.append(
            "Your program **did not finish** within the time limit for this test.\n\n"
            "Common causes:\n"
            "• An infinite loop (missing or wrong loop termination condition)\n"
            "• Waiting for input that never comes (extra scanf)\n"
            "• Recursive function without a proper base case"
        )
        if inp:
            lines.append(f"\nInput given: `{inp.strip()[:80]}`")

    elif rerr:
        lines.append(
            f"Your program **crashed** (exit code {ec}) on this test.\n\n"
            "Common causes:\n"
            "• Segmentation fault — reading/writing outside array bounds\n"
            "• Division by zero — check all divisions\n"
            "• NULL pointer dereference — check pointer initialisation"
        )
        if inp:
            lines.append(f"\nInput given: `{inp.strip()[:80]}`")

    else:
        lines.append("Your output **did not match** the expected output.\n")
        if inp:
            lines.append(f"**Input:** `{inp.strip()[:80]}`")
        lines.append(f"**Expected:** `{exp.strip()[:80]}`")
        lines.append(f"**Your output:** `{act.strip()[:80] if act else '(empty)'}`")
        if hint:
            lines.append(f"\n🔍 {hint}")

        # Specific pattern hints
        if exp.strip().lstrip('-').isdigit() and act.strip().lstrip('-').isdigit():
            try:
                diff = int(act.strip()) - int(exp.strip())
                if diff != 0:
                    lines.append(
                        f"\n💡 Your answer is off by **{abs(diff)}**. "
                        "Check your arithmetic logic."
                    )
            except ValueError:
                pass

        if exp.strip() == "" and act.strip() != "":
            lines.append(
                "\n💡 The expected output is empty but your program printed something. "
                "Check for extra printf calls."
            )

        if act.strip() == "" and exp.strip() != "":
            lines.append(
                "\n💡 Your program produced no output. "
                "Check that printf is called and the format string is correct."
            )

    return FeedbackSection(
        title=f"Test {tid} Failed — {desc}",
        body="\n".join(lines),
        level="error" if rerr or tout else "warning",
    )


# ── Static analysis feedback ──────────────────────────────────────────────────

def _feedback_from_static_analysis(sa: dict) -> list[FeedbackSection]:
    """Convert static analysis warnings into FeedbackSections."""
    sections: list[FeedbackSection] = []
    if not sa:
        return sections

    warnings = sa.get("warnings", [])
    for w in warnings:
        level = "warning"
        code_hint = None

        if "goto" in w.lower():
            code_hint = textwrap.dedent("""\
                /* Avoid goto — use structured control flow instead */
                /* ❌ goto bad practice: */
                if (error) goto cleanup;

                /* ✅ Use a function or structured return instead */
                if (error) { cleanup(); return -1; }
            """)

        elif "gets" in w.lower():
            level = "error"
            code_hint = textwrap.dedent("""\
                /* ❌ gets() is dangerous — removed in C11 */
                gets(buffer);

                /* ✅ Use fgets() with a size limit instead */
                fgets(buffer, sizeof(buffer), stdin);
            """)
            w = w + " — This is a security vulnerability."

        elif "malloc" in w.lower() and "free" in w.lower():
            code_hint = textwrap.dedent("""\
                /* ✅ Always free what you malloc */
                int *arr = malloc(n * sizeof(int));
                if (arr == NULL) { /* handle error */ return -1; }
                /* ... use arr ... */
                free(arr);   /* ← don't forget this! */
                arr = NULL;  /* ← good practice */
            """)

        elif "global" in w.lower():
            code_hint = textwrap.dedent("""\
                /* ❌ Avoid global mutable variables */
                int counter = 0;  /* global — hard to test, creates side effects */

                /* ✅ Pass state as function parameters instead */
                int increment(int counter) { return counter + 1; }
            """)

        elif "magic number" in w.lower():
            code_hint = textwrap.dedent("""\
                /* ❌ Magic numbers make code hard to understand */
                if (score >= 10) { ... }

                /* ✅ Use named constants */
                #define PASSING_SCORE 10
                if (score >= PASSING_SCORE) { ... }
            """)

        sections.append(FeedbackSection(
            title="Code Quality Warning",
            body=w,
            level=level,
            code=code_hint,
        ))

    # Complexity feedback
    complexity = sa.get("cyclomatic_complexity", 1)
    if complexity > 10:
        sections.append(FeedbackSection(
            title="High Cyclomatic Complexity",
            body=(
                f"Your code has a cyclomatic complexity of **{complexity}**, "
                "which is quite high. This means your code has many branching paths "
                "and may be difficult to test and maintain.\n\n"
                "Consider breaking large functions into smaller, focused helper functions."
            ),
            level="tip",
        ))

    # Recursion without base case hint
    funcs = sa.get("functions", [])
    for fn in funcs:
        if fn.get("is_recursive"):
            sections.append(FeedbackSection(
                title=f"Recursive Function: {fn['name']}()",
                body=(
                    f"`{fn['name']}()` calls itself recursively. "
                    "Make sure you have:\n"
                    "1. A **base case** that stops the recursion\n"
                    "2. Each recursive call moves **closer** to the base case\n"
                    "Otherwise your program will crash with a stack overflow."
                ),
                level="tip",
                code=textwrap.dedent(f"""\
                    int {fn['name']}(int n) {{
                        /* Base case — stops recursion */
                        if (n <= 0) return 0;
                        /* Recursive step — moves toward base case */
                        return n + {fn['name']}(n - 1);
                    }}
                """),
            ))

    return sections


# ── Summary section ───────────────────────────────────────────────────────────

def _build_summary_section(
    score:       float,
    max_score:   float,
    grade_label: str,
    tests_passed:int,
    tests_total: int,
    is_late:     bool,
    late_penalty:float,
    compile_warnings: list[str],
) -> FeedbackSection:
    pct = (score / max_score * 100) if max_score else 0

    if grade_label == "Perfect":
        body = (
            f"🏆 **Perfect score!** You passed all {tests_total} test cases "
            f"and scored {score}/{max_score}.\n\n"
            "Excellent work — your solution is correct and complete."
        )
        level = "success"

    elif grade_label == "Excellent":
        body = (
            f"🌟 **Excellent work!** You scored {score}/{max_score} ({pct:.0f}%) "
            f"and passed {tests_passed}/{tests_total} tests.\n\n"
            "You are very close to a perfect score. Review the failed test(s) below."
        )
        level = "success"

    elif grade_label == "Good":
        body = (
            f"👍 **Good job.** You scored {score}/{max_score} ({pct:.0f}%) "
            f"and passed {tests_passed}/{tests_total} tests.\n\n"
            "Your solution handles most cases correctly. "
            "Focus on the failed tests — they likely reveal edge cases you haven't handled."
        )
        level = "info"

    elif grade_label == "Pass":
        body = (
            f"✅ **Passing grade.** You scored {score}/{max_score} ({pct:.0f}%) "
            f"and passed {tests_passed}/{tests_total} tests.\n\n"
            "You met the minimum passing threshold. "
            "Work through the failed tests to improve your score."
        )
        level = "info"

    elif grade_label == "Needs Work":
        body = (
            f"⚠️ **Needs improvement.** You scored {score}/{max_score} ({pct:.0f}%) "
            f"and passed only {tests_passed}/{tests_total} tests.\n\n"
            "Your program runs but produces incorrect results for most inputs. "
            "Start by fixing the logic for the first failing test, then re-submit."
        )
        level = "warning"

    else:   # Fail
        if tests_passed == 0 and tests_total > 0:
            body = (
                f"❌ **No tests passed.** You scored {score}/{max_score}.\n\n"
                "Your program compiles but does not produce correct output for any test. "
                "Re-read the assignment requirements and check what your program actually prints."
            )
        else:
            body = (
                f"❌ **Below passing threshold.** You scored {score}/{max_score} ({pct:.0f}%) "
                f"and passed {tests_passed}/{tests_total} tests.\n\n"
                "Review the error details below carefully."
            )
        level = "error"

    extras: list[str] = []
    if is_late and late_penalty > 0:
        extras.append(
            f"⏰ A **{late_penalty:.2f} point** late penalty was applied to your score."
        )
    if compile_warnings:
        extras.append(
            f"⚠️ Your code compiled with **{len(compile_warnings)} warning(s)**. "
            "Warnings often hide bugs — fix them even if the code runs."
        )

    if extras:
        body += "\n\n" + "\n".join(extras)

    return FeedbackSection(title="Summary", body=body, level=level)


# ── LLM feedback (Layer 2) ────────────────────────────────────────────────────

def _call_llm_feedback(
    source_code:   str,
    failed_tests:  list[dict],
    sa:            dict,
    score:         float,
    max_score:     float,
    grade_label:   str,
) -> Optional[str]:
    """
    Call the Anthropic API to generate rich natural-language feedback.
    Returns a markdown string, or None on failure.
    Requires ANTHROPIC_API_KEY in the environment.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        logger.debug("ANTHROPIC_API_KEY not set — skipping LLM feedback")
        return None

    try:
        import anthropic

        # Build a tight, focused prompt
        failed_summary = ""
        for t in failed_tests[:4]:   # max 4 to stay within token budget
            failed_summary += (
                f"\n- Test '{t.get('description', '')}': "
                f"input={repr(t.get('input',''))[:40]}, "
                f"expected={repr(t.get('expected_output',''))[:40]}, "
                f"got={repr(t.get('actual_output',''))[:40]}"
            )
            if t.get('timed_out'):
                failed_summary += " [TIMEOUT]"
            elif t.get('runtime_error'):
                failed_summary += f" [CRASH exit={t.get('exit_code')}]"

        warnings_text = "\n".join(f"- {w}" for w in sa.get("warnings", []))
        funcs_text    = ", ".join(sa.get("function_names", []))
        complexity    = sa.get("cyclomatic_complexity", 1)

        # Truncate source to 3000 chars to respect token limits
        source_snippet = source_code[:3000]
        if len(source_code) > 3000:
            source_snippet += "\n... [truncated]"

        prompt = textwrap.dedent(f"""\
            You are a C programming teaching assistant reviewing a student's submission.

            SCORE: {score}/{max_score} ({grade_label})

            STUDENT SOURCE CODE:
```c
            {source_snippet}
```

            FAILED TESTS:{failed_summary if failed_summary else " (none — all tests passed)"}

            STATIC ANALYSIS:
            - Functions: {funcs_text or 'none'}
            - Cyclomatic complexity: {complexity}
            - Warnings: {warnings_text or 'none'}

            Write concise, constructive feedback for the student (max 200 words).
            Focus on:
            1. The most important bug causing failures (if any)
            2. One specific code improvement suggestion
            3. One encouraging sentence

            Do NOT repeat the test cases verbatim.
            Do NOT write code for the student — give hints only.
            Use plain text with minimal markdown.
        """)

        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text.strip()

    except Exception as exc:
        logger.warning("LLM feedback failed: %s", exc)
        return None


# ── Main public entry point ───────────────────────────────────────────────────

def generate_feedback(
    submission_id:    int,
    score:            float,
    max_score:        float,
    grade_label:      str,
    compile_output:   str,
    test_results:     list[dict],
    static_analysis:  dict,
    is_late:          bool          = False,
    late_penalty:     float         = 0.0,
    source_path:      Optional[Path] = None,
    use_llm:          bool          = True,
) -> FeedbackReport:
    """
    Generate a complete FeedbackReport for a submission.

    Parameters
    ──────────
    submission_id   DB id of the submission
    score           final score after penalties
    max_score       maximum possible score
    grade_label     "Perfect"|"Excellent"|"Good"|"Pass"|"Needs Work"|"Fail"
    compile_output  raw GCC stdout+stderr
    test_results    list of per-test result dicts from evaluation_service
    static_analysis dict from static_analysis_service
    is_late         whether submission was late
    late_penalty    points deducted for lateness
    source_path     Path to .c file (needed for LLM feedback)
    use_llm         whether to attempt LLM layer (default True)
    """
    tests_passed = sum(1 for t in test_results if t.get("passed"))
    tests_total  = len(test_results)
    pass_rate    = tests_passed / tests_total if tests_total else 0.0
    compile_warnings = [l for l in (compile_output or "").splitlines()
                        if ": warning:" in l]

    report = FeedbackReport(
        submission_id = submission_id,
        grade_label   = grade_label,
        score         = score,
        max_score     = max_score,
        pass_rate     = pass_rate,
    )

    # ── 1. Summary section ───────────────────────────────────────
    report.sections.append(_build_summary_section(
        score, max_score, grade_label,
        tests_passed, tests_total,
        is_late, late_penalty, compile_warnings,
    ))

    # ── 2. Compile errors ────────────────────────────────────────
    compile_sections = _parse_gcc_errors(compile_output or "")
    report.sections.extend(compile_sections)

    # ── 3. Failed test feedback ──────────────────────────────────
    failed = [t for t in test_results if not t.get("passed")]
    for t in failed[:5]:   # cap at 5 for readability
        report.sections.append(_feedback_for_failed_test(t))

    if len(failed) > 5:
        report.sections.append(FeedbackSection(
            title=f"… and {len(failed) - 5} more failed test(s)",
            body="Fix the issues above and re-submit to see feedback for remaining tests.",
            level="info",
        ))

    # ── 4. Static analysis feedback ──────────────────────────────
    sa_sections = _feedback_from_static_analysis(static_analysis or {})
    report.sections.extend(sa_sections)

    # ── 5. LLM layer ─────────────────────────────────────────────
    llm_text = None
    if use_llm and (failed or sa_sections) and source_path and source_path.exists():
        try:
            source_code = source_path.read_text(errors="replace")
            llm_text = _call_llm_feedback(
                source_code  = source_code,
                failed_tests = failed[:4],
                sa           = static_analysis or {},
                score        = score,
                max_score    = max_score,
                grade_label  = grade_label,
            )
            if llm_text:
                report.sections.append(FeedbackSection(
                    title="AI Teaching Assistant Suggestions",
                    body=llm_text,
                    level="tip",
                ))
                report.generated_by_llm = True
        except Exception as exc:
            logger.warning("LLM feedback failed: %s", exc)
            report.llm_error = str(exc)

    # ── 6. Plain-text summary ─────────────────────────────────────
    report.summary = _build_plain_summary(report)

    return report


def _build_plain_summary(report: FeedbackReport) -> str:
    """Build a backwards-compatible plain-text summary."""
    lines = [
        f"Score: {report.score}/{report.max_score} ({report.grade_label})",
        f"Tests: {int(report.pass_rate * 100)}% passed",
    ]
    for s in report.sections:
        if s.level in ("error", "warning"):
            # Include first line of each error/warning
            first_line = s.body.split("\n")[0].replace("**", "")
            lines.append(f"• {s.title}: {first_line[:80]}")
    return "\n".join(lines)


def feedback_report_to_dict(report: FeedbackReport) -> dict:
    """Serialise FeedbackReport to a JSON-safe dict."""
    return {
        "submission_id":    report.submission_id,
        "grade_label":      report.grade_label,
        "score":            report.score,
        "max_score":        report.max_score,
        "pass_rate":        round(report.pass_rate, 3),
        "generated_by_llm": report.generated_by_llm,
        "llm_error":        report.llm_error,
        "summary":          report.summary,
        "sections": [
            {
                "title": s.title,
                "body":  s.body,
                "level": s.level,
                "code":  s.code,
            }
            for s in report.sections
        ],
    }