"""
test_generator.py
─────────────────
- Score always /20
- Test count = n_inputs × n_inputs (corpus size squared)
- Claude fallback when execution fails
- Auto-trigger after publish
"""

import re
import random
import logging
import textwrap
import json
from pathlib import Path
from typing import Optional

from app.services.static_analysis import analyse_c_file, StaticAnalysisResult

logger = logging.getLogger(__name__)

MAX_SCORE         = 20.0   # always /20
DEFAULT_TIMEOUT_S = 8
DEFAULT_WEIGHT    = 1.0
MAX_TEST_COUNT    = 50     # hard ceiling


class InputPattern:
    NONE          = "none"
    SINGLE_INT    = "single_int"
    TWO_INTS      = "two_ints"
    THREE_INTS    = "three_ints"
    SINGLE_FLOAT  = "single_float"
    TWO_FLOATS    = "two_floats"
    SINGLE_STRING = "single_string"
    INT_ARRAY     = "int_array"
    UNKNOWN       = "unknown"


# ── Corpus builders ───────────────────────────────────────────

def _int_values() -> list[int]:
    return [0, 1, -1, 2, -2, 10, -10, 100, -100, 127,
            *[random.randint(-50, 50) for _ in range(4)]]

def _float_values() -> list[float]:
    return [0.0, 1.0, -1.0, 0.5, 3.14, 100.0,
            *[round(random.uniform(-50, 50), 2) for _ in range(4)]]

def _string_values() -> list[str]:
    return ["hello", "world", "test", "a", "Algeria", "abc123"]


# ── Auto count: n × n ─────────────────────────────────────────

def _auto_count(pattern: str) -> int:
    """
    Compute n_values for the pattern, return n_values * n_values.
    Capped at MAX_TEST_COUNT.
    """
    size_map = {
        InputPattern.NONE:          3,    # 3×3 = 9 but capped to 3
        InputPattern.SINGLE_INT:    4,    # 4×4 = 16
        InputPattern.TWO_INTS:      4,    # 4×4 = 16
        InputPattern.THREE_INTS:    3,    # 3×3 = 9
        InputPattern.SINGLE_FLOAT:  4,    # 4×4 = 16
        InputPattern.TWO_FLOATS:    3,    # 3×3 = 9
        InputPattern.SINGLE_STRING: 3,    # 3×3 = 9
        InputPattern.INT_ARRAY:     3,    # 3×3 = 9
        InputPattern.UNKNOWN:       3,    # 3×3 = 9
    }
    n   = size_map.get(pattern, 4)
    cnt = n * n
    return min(cnt, MAX_TEST_COUNT)


# ── Pattern detection ─────────────────────────────────────────

def _detect_input_pattern(source_path: Path, analysis: StaticAnalysisResult) -> str:
    try:
        source = source_path.read_text(errors="replace")
    except Exception:
        return InputPattern.UNKNOWN

    if not analysis.uses_scanf:
        return InputPattern.NONE

    fmts = re.findall(r'\bscanf\s*\(\s*"([^"]+)"', source)
    if not fmts:
        return InputPattern.SINGLE_FLOAT if re.search(
            r'\bfloat\b|\bdouble\b', source) else InputPattern.SINGLE_INT

    combined = " ".join(fmts)
    d = combined.count("%d") + combined.count("%i")
    f = combined.count("%f") + combined.count("%lf") + combined.count("%g")
    s = combined.count("%s")

    if f >= 2:  return InputPattern.TWO_FLOATS
    if f == 1:  return InputPattern.SINGLE_FLOAT
    if d >= 3:  return InputPattern.THREE_INTS
    if d == 2:  return InputPattern.TWO_INTS
    if d == 1:  return InputPattern.SINGLE_INT
    if s >= 1:  return InputPattern.SINGLE_STRING
    if re.search(r'(for|while)[^;]*scanf', source, re.DOTALL):
        return InputPattern.INT_ARRAY
    return InputPattern.UNKNOWN


# ── Input generator (n × n combinations) ─────────────────────

def _generate_raw_inputs(pattern: str, n: int) -> list[str]:
    """
    Generate n×n unique inputs for the given pattern.
    Each "axis" has n values; we take cartesian product.
    """
    inputs: list[str] = []

    if pattern == InputPattern.NONE:
        return [""] * min(n * n, 3)

    elif pattern == InputPattern.SINGLE_INT:
        vals = _int_values()[:n]
        # n×n: repeat with different orderings (shuffle variants)
        for v in vals:
            for _ in range(n):
                inputs.append(str(v))
        # deduplicate — just use the n distinct values × n = n unique
        # For single input, n×n means n² tries but we only have n unique vals
        # Better: use all pairs as (v,) — just n unique inputs
        inputs = [str(v) for v in _int_values()[:n*n]]

    elif pattern == InputPattern.TWO_INTS:
        vals = _int_values()[:n]
        for a in vals:
            for b in vals:
                inputs.append(f"{a} {b}")

    elif pattern == InputPattern.THREE_INTS:
        vals = _int_values()[:n]
        for a in vals:
            for b in vals:
                inputs.append(f"{a} {b} {a+b}")
                if len(inputs) >= n * n:
                    break

    elif pattern == InputPattern.SINGLE_FLOAT:
        vals = _float_values()[:n*n]
        inputs = [str(v) for v in vals]

    elif pattern == InputPattern.TWO_FLOATS:
        vals = _float_values()[:n]
        for a in vals:
            for b in vals:
                inputs.append(f"{a} {b}")

    elif pattern == InputPattern.SINGLE_STRING:
        strs = _string_values()[:n]
        for s in strs:
            for _ in range(n):
                inputs.append(s)
        inputs = list(dict.fromkeys(inputs))   # deduplicate preserving order

    elif pattern == InputPattern.INT_ARRAY:
        for sz in range(1, n + 1):
            for _ in range(n):
                vals = [random.randint(1, 20) for _ in range(sz)]
                inputs.append(f"{sz}\n" + " ".join(map(str, vals)))

    else:
        inputs = ["", "1", "0", "1 2", "5 3", "-1 0", "10 20", "3 4", "0 0"]

    # Deduplicate preserving order
    seen, result = set(), []
    for inp in inputs:
        key = inp.strip()
        if key not in seen:
            seen.add(key)
            result.append(inp)

    return result[:n * n]


# ── Reference runner ──────────────────────────────────────────

def _run_reference(
    source_path: Path,
    stdin_input: str,
    timeout_s:   int = DEFAULT_TIMEOUT_S,
) -> Optional[str]:
    try:
        from app.services.execution_service import run_c_binary
        result = run_c_binary(
            source_path = source_path,
            stdin_input = stdin_input if stdin_input.strip() else None,
            timeout_s   = timeout_s,
        )
        if result.timed_out or not result.success:
            return None
        return result.stdout.strip()
    except Exception as exc:
        logger.error("Reference run failed: %s", exc)
        return None


def _verify_compiles(source_path: Path) -> tuple[bool, str]:
    try:
        from app.services.execution_service import compile_c_file
        r = compile_c_file(source_path)
        return r.success, r.output
    except Exception as exc:
        return False, str(exc)


# ── Description ───────────────────────────────────────────────

def _desc(tc_id: int, inp: str, pattern: str) -> str:
    base = {
        InputPattern.NONE:         "No input",
        InputPattern.SINGLE_INT:   f"Input: {inp}",
        InputPattern.TWO_INTS:     f"Inputs: {inp}",
        InputPattern.THREE_INTS:   f"Inputs: {inp}",
        InputPattern.SINGLE_FLOAT: f"Float: {inp}",
        InputPattern.TWO_FLOATS:   f"Floats: {inp}",
        InputPattern.SINGLE_STRING:f"String: '{inp}'",
        InputPattern.INT_ARRAY:    f"Array: {inp[:20]}",
        InputPattern.UNKNOWN:      f"Test {tc_id}",
    }.get(pattern, f"Test {tc_id}")

    tags = []
    if inp.strip() in ("0", "0 0", ""):
        tags.append("zero")
    if re.search(r'(?<!\d)-\d', inp):
        tags.append("negative")
    return base + (f" [{', '.join(tags)}]" if tags else "")


# ── Weight assignment (always sums to 20) ─────────────────────

def _assign_weights(test_cases: list[dict]) -> list[dict]:
    """Distribute 20 points across all test cases."""
    if not test_cases:
        return test_cases

    def _is_edge(tc):
        inp = tc.get("input", "").strip()
        return inp in ("0", "0 0", "", "-1", "1")

    raw = [1.5 if _is_edge(tc) else 1.0 for tc in test_cases]
    total = sum(raw)
    scale = MAX_SCORE / total if total > 0 else 1.0

    for tc, rw in zip(test_cases, raw):
        tc["weight"]    = round(rw * scale, 4)
        tc["max_score"] = MAX_SCORE   # always /20

    return test_cases


# ── Claude fallback ───────────────────────────────────────────

def _claude_fallback(
    source_code:   str,
    desired_count: int,
) -> list[dict]:
    api_key = __import__('os').environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return []
    try:
        import anthropic
        prompt = textwrap.dedent(f"""\
            You are a C test case generator. Analyse this C program and generate
            exactly {desired_count} test cases covering normal, edge, and boundary cases.

            SOURCE:
```c
            {source_code[:3000]}
```

            Return ONLY a JSON array. No markdown, no explanation.
            Format: [{{"id":1,"description":"...","input":"...","expected_output":"..."}}]
            Input is the exact stdin string. Expected_output is exact stdout.
            Generate {desired_count} test cases:
        """)
        client  = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model      = "claude-haiku-4-5-20251001",
            max_tokens = 2000,
            messages   = [{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()
        raw = re.sub(r'^```json\s*', '', raw)
        raw = re.sub(r'^```\s*',     '', raw)
        raw = re.sub(r'\s*```$',     '', raw)
        cases = json.loads(raw)
        result = []
        for i, tc in enumerate(cases[:desired_count], 1):
            result.append({
                "id":              i,
                "description":     tc.get("description", f"Test {i}"),
                "input":           str(tc.get("input", "")),
                "expected_output": str(tc.get("expected_output", "")),
                "weight":          1.0,
                "max_score":       MAX_SCORE,
                "norm_mode":       "strip",
                "timeout_seconds": DEFAULT_TIMEOUT_S,
            })
        logger.info("Claude generated %d test cases", len(result))
        return _assign_weights(result)
    except Exception as exc:
        logger.error("Claude fallback failed: %s", exc)
        return []


# ── Main entry point ──────────────────────────────────────────

def generate_test_cases(
    reference_solution_path: Path,
    timeout_s: int = DEFAULT_TIMEOUT_S,
) -> list[dict]:
    """
    Generate test cases automatically.
    Count = n_values × n_values based on detected input pattern.
    Score always /20.
    Falls back to Claude API if execution fails.
    """
    logger.info("Generating test cases from '%s'",
                reference_solution_path.name)

    if not reference_solution_path.exists():
        logger.error("File not found: %s", reference_solution_path)
        return []

    source_code = reference_solution_path.read_text(errors="replace")

    # Compile check
    compiled, compile_output = _verify_compiles(reference_solution_path)
    if not compiled:
        logger.warning("Does not compile — trying Claude: %s", compile_output[:100])
        return _claude_fallback(source_code, 16)

    # Static analysis
    try:
        analysis = analyse_c_file(reference_solution_path)
    except Exception:
        from app.services.static_analysis import StaticAnalysisResult
        analysis             = StaticAnalysisResult()
        analysis.has_main    = True
        analysis.uses_scanf  = True

    if not analysis.has_main:
        return _claude_fallback(source_code, 16)

    # Detect pattern
    pattern       = _detect_input_pattern(reference_solution_path, analysis)
    n             = int((MAX_TEST_COUNT ** 0.5))   # sqrt of max → n per axis
    # compute proper n from pattern
    size_map = {
        InputPattern.NONE:          2,
        InputPattern.SINGLE_INT:    4,
        InputPattern.TWO_INTS:      4,
        InputPattern.THREE_INTS:    3,
        InputPattern.SINGLE_FLOAT:  4,
        InputPattern.TWO_FLOATS:    3,
        InputPattern.SINGLE_STRING: 3,
        InputPattern.INT_ARRAY:     3,
        InputPattern.UNKNOWN:       3,
    }
    n             = size_map.get(pattern, 4)
    desired_count = min(n * n, MAX_TEST_COUNT)

    logger.info("Pattern=%s  n=%d  target=%d test cases", pattern, n, desired_count)

    # Generate inputs (n×n combinations)
    raw_inputs = _generate_raw_inputs(pattern, n)
    logger.info("Generated %d raw input candidates", len(raw_inputs))

    # Run reference
    test_cases: list[dict] = []
    tc_id = 1
    for stdin_input in raw_inputs:
        if len(test_cases) >= desired_count:
            break
        expected = _run_reference(reference_solution_path, stdin_input, timeout_s)
        if expected is None:
            continue
        if expected == "" and pattern != InputPattern.NONE:
            continue
        test_cases.append({
            "id":              tc_id,
            "description":     _desc(tc_id, stdin_input, pattern),
            "input":           stdin_input,
            "expected_output": expected,
            "weight":          1.0,
            "max_score":       MAX_SCORE,
            "norm_mode":       "strip",
            "timeout_seconds": timeout_s,
        })
        tc_id += 1

    logger.info("Execution produced %d test cases", len(test_cases))

    if len(test_cases) < max(1, desired_count // 2):
        logger.warning("Too few — trying Claude fallback")
        claude = _claude_fallback(source_code, desired_count)
        if claude:
            return claude

    return _assign_weights(test_cases) if test_cases else []


def generate_from_custom_inputs(
    reference_solution_path: Path,
    custom_inputs: list[str],
    timeout_s:     int = DEFAULT_TIMEOUT_S,
) -> list[dict]:
    if not reference_solution_path.exists():
        return []
    compiled, _ = _verify_compiles(reference_solution_path)
    if not compiled:
        return []

    try:
        analysis = analyse_c_file(reference_solution_path)
        pattern  = _detect_input_pattern(reference_solution_path, analysis)
    except Exception:
        pattern  = InputPattern.UNKNOWN

    test_cases = []
    for i, inp in enumerate(custom_inputs, 1):
        expected = _run_reference(reference_solution_path, inp, timeout_s)
        if expected is None:
            continue
        test_cases.append({
            "id":              i,
            "description":     _desc(i, inp, pattern),
            "input":           inp,
            "expected_output": expected,
            "weight":          1.0,
            "max_score":       MAX_SCORE,
            "norm_mode":       "strip",
            "timeout_seconds": timeout_s,
        })

    return _assign_weights(test_cases)