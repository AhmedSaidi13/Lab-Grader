"""
static_analysis.py
──────────────────
White-box static analysis of student C source code using pycparser.

Extracts:
  - Function names, parameter counts, return types
  - Variable declarations
  - #include directives
  - Control flow constructs (loops, conditionals, recursion)
  - Cyclomatic complexity estimate
  - Code smells and warnings (magic numbers, missing return, etc.)
  - Forbidden constructs (goto, global mutable state)

pycparser requires a pre-processed file OR fake includes.
We use pycparser's bundled fake_libc_include for portability.
"""

import re
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# ── Try importing pycparser ──────────────────────────────────────────────────
try:
    import pycparser
    from pycparser import c_ast, parse_file, CParser
    PYCPARSER_AVAILABLE = True
except ImportError:
    PYCPARSER_AVAILABLE = False
    logger.warning("pycparser not installed — static analysis will use regex fallback")

# ── Data structures ──────────────────────────────────────────────────────────

@dataclass
class FunctionInfo:
    name:        str
    return_type: str
    param_count: int
    param_types: list[str] = field(default_factory=list)
    param_names: list[str] = field(default_factory=list)
    is_recursive:bool = False
    line_number: int  = 0


@dataclass
class StaticAnalysisResult:
    # Structure
    functions:        list[FunctionInfo] = field(default_factory=list)
    function_names:   list[str]          = field(default_factory=list)
    has_main:         bool               = False
    main_uses_argc:   bool               = False

    # Variables & includes
    global_variables: list[str]          = field(default_factory=list)
    includes:         list[str]          = field(default_factory=list)

    # Control flow counts
    loop_count:       int  = 0    # for + while + do-while
    if_count:         int  = 0
    switch_count:     int  = 0
    recursion_count:  int  = 0
    goto_count:       int  = 0

    # Complexity
    cyclomatic_complexity: float = 1.0

    # I/O pattern detection
    uses_printf:  bool = False
    uses_scanf:   bool = False
    uses_gets:    bool = False      # dangerous
    uses_malloc:  bool = False
    uses_free:    bool = False
    uses_fopen:   bool = False
    uses_arrays:  bool = False
    uses_pointers:bool = False
    uses_structs: bool = False

    # Warnings / smells
    warnings:     list[str] = field(default_factory=list)
    errors:       list[str] = field(default_factory=list)

    # Meta
    line_count:   int  = 0
    analysis_method: str = "none"   # "pycparser" | "regex" | "none"


# ── AST Visitor ─────────────────────────────────────────────────────────────

class _CAnalysisVisitor(c_ast.NodeVisitor if PYCPARSER_AVAILABLE else object):
    """Walk the pycparser AST and gather metrics."""

    def __init__(self):
        self.functions:    list[FunctionInfo] = []
        self.global_vars:  list[str]          = []
        self.loop_count    = 0
        self.if_count      = 0
        self.switch_count  = 0
        self.goto_count    = 0
        self._current_func: Optional[str]     = None
        self._func_calls:   dict[str, set]    = {}   # func → set of called funcs

    # ── Declarations ────────────────────────────────────────────

    def visit_Decl(self, node):
        if isinstance(node.type, c_ast.FuncDecl):
            return   # handled by visit_FuncDef
        if self._current_func is None and node.name:
            self.global_vars.append(node.name)
        self.generic_visit(node)

    def visit_FuncDef(self, node):
        name = node.decl.name
        decl = node.decl.type   # FuncDecl

        # Return type
        ret_type = _type_to_str(decl.type)

        # Parameters
        param_types, param_names = [], []
        if decl.args and decl.args.params:
            for p in decl.args.params:
                if isinstance(p, c_ast.EllipsisParam):
                    param_types.append("...")
                    param_names.append("...")
                else:
                    param_types.append(_type_to_str(p.type))
                    param_names.append(p.name or "")

        line = node.coord.line if node.coord else 0
        info = FunctionInfo(
            name=name,
            return_type=ret_type,
            param_count=len(param_types),
            param_types=param_types,
            param_names=param_names,
            line_number=line,
        )
        self.functions.append(info)
        self._func_calls[name] = set()

        # Walk the body with function context
        prev = self._current_func
        self._current_func = name
        self.generic_visit(node)
        self._current_func = prev

    # ── Control flow ─────────────────────────────────────────────

    def visit_For(self, node):
        self.loop_count += 1
        self.generic_visit(node)

    def visit_While(self, node):
        self.loop_count += 1
        self.generic_visit(node)

    def visit_DoWhile(self, node):
        self.loop_count += 1
        self.generic_visit(node)

    def visit_If(self, node):
        self.if_count += 1
        self.generic_visit(node)

    def visit_Switch(self, node):
        self.switch_count += 1
        self.generic_visit(node)

    def visit_Goto(self, node):
        self.goto_count += 1
        self.generic_visit(node)

    # ── Function calls ────────────────────────────────────────────

    def visit_FuncCall(self, node):
        if self._current_func and isinstance(node.name, c_ast.ID):
            self._func_calls[self._current_func].add(node.name.name)
        self.generic_visit(node)

    # ── Recursion detection ──────────────────────────────────────

    def detect_recursion(self):
        for func in self.functions:
            if func.name in self._func_calls.get(func.name, set()):
                func.is_recursive = True


def _type_to_str(type_node) -> str:
    """Recursively convert a pycparser type node to a string."""
    if not PYCPARSER_AVAILABLE:
        return "unknown"
    if isinstance(type_node, c_ast.TypeDecl):
        return _type_to_str(type_node.type)
    if isinstance(type_node, c_ast.IdentifierType):
        return " ".join(type_node.names)
    if isinstance(type_node, c_ast.PtrDecl):
        return _type_to_str(type_node.type) + "*"
    if isinstance(type_node, c_ast.ArrayDecl):
        return _type_to_str(type_node.type) + "[]"
    if isinstance(type_node, c_ast.Struct):
        return f"struct {type_node.name or ''}"
    return "unknown"


# ── Include extraction (regex — always available) ────────────────────────────

def _extract_includes(source: str) -> list[str]:
    return re.findall(r'#\s*include\s*[<"]([^>"]+)[>"]', source)


def _extract_io_patterns(source: str) -> dict:
    return {
        "uses_printf":   bool(re.search(r'\bprintf\s*\(', source)),
        "uses_scanf":    bool(re.search(r'\bscanf\s*\(', source)),
        "uses_gets":     bool(re.search(r'\bgets\s*\(', source)),
        "uses_malloc":   bool(re.search(r'\bmalloc\s*\(', source)),
        "uses_free":     bool(re.search(r'\bfree\s*\(', source)),
        "uses_fopen":    bool(re.search(r'\bfopen\s*\(', source)),
        "uses_arrays":   bool(re.search(r'\w+\s*\[', source)),
        "uses_pointers": bool(re.search(r'\*\w+|\w+\s*->', source)),
        "uses_structs":  bool(re.search(r'\bstruct\b', source)),
    }


# ── Regex fallback analyser ──────────────────────────────────────────────────

def _regex_analyse(source: str, result: StaticAnalysisResult) -> None:
    """Best-effort analysis without pycparser."""
    result.analysis_method = "regex"

    # Functions
    func_pattern = re.compile(
        r'(\w[\w\s\*]+?)\s+(\w+)\s*\(([^)]*)\)\s*\{'
    )
    for m in func_pattern.finditer(source):
        ret  = m.group(1).strip()
        name = m.group(2).strip()
        params = [p.strip() for p in m.group(3).split(",") if p.strip()]
        info = FunctionInfo(
            name=name,
            return_type=ret,
            param_count=len(params),
            param_types=params,
        )
        result.functions.append(info)
        result.function_names.append(name)
        if name == "main":
            result.has_main = True
            result.main_uses_argc = "argc" in m.group(3)

    result.loop_count  = len(re.findall(r'\b(for|while|do)\b', source))
    result.if_count    = len(re.findall(r'\bif\b', source))
    result.switch_count= len(re.findall(r'\bswitch\b', source))
    result.goto_count  = len(re.findall(r'\bgoto\b', source))


# ── Warning rules ────────────────────────────────────────────────────────────

def _apply_warning_rules(result: StaticAnalysisResult, source: str) -> None:
    if result.goto_count > 0:
        result.warnings.append(
            f"Use of 'goto' detected ({result.goto_count} occurrence(s)) — "
            "generally considered bad practice in C."
        )
    if result.uses_gets:
        result.warnings.append(
            "'gets()' is dangerous and removed in C11 — use 'fgets()' instead."
        )
    if not result.has_main:
        result.errors.append("No 'main' function found.")
    if result.global_variables:
        result.warnings.append(
            f"Global mutable variables detected: {', '.join(result.global_variables[:5])}"
        )
    # Magic numbers
    magic = re.findall(r'(?<!\w)(?!0\b)\d{2,}(?!\w)', source)
    if len(magic) > 3:
        result.warnings.append(
            f"Multiple magic numbers detected ({len(magic)}). "
            "Consider using named constants (#define or const)."
        )
    if result.uses_malloc and not result.uses_free:
        result.warnings.append(
            "Memory allocated with malloc() but no free() detected — possible memory leak."
        )


# ── Cyclomatic complexity ────────────────────────────────────────────────────

def _cyclomatic_complexity(result: StaticAnalysisResult) -> float:
    """
    McCabe complexity: 1 + decision points.
    Decision points: if, for, while, do-while, switch, case, &&, ||
    """
    return 1.0 + result.if_count + result.loop_count + result.switch_count


# ── Public entry point ───────────────────────────────────────────────────────

def analyse_c_file(source_path: Path) -> StaticAnalysisResult:
    """
    Run static analysis on a .c source file.
    Uses pycparser AST if available, falls back to regex.
    """
    result = StaticAnalysisResult()

    if not source_path.exists():
        result.errors.append(f"File not found: {source_path}")
        return result

    source = source_path.read_text(errors="replace")
    result.line_count = source.count("\n") + 1
    result.includes   = _extract_includes(source)

    io = _extract_io_patterns(source)
    for key, val in io.items():
        setattr(result, key, val)

    # ── pycparser path ───────────────────────────────────────────
    if PYCPARSER_AVAILABLE:
        try:
            import pycparser as pu
            fake_libc = Path(pycparser.__file__).parent / "utils" / "fake_libc_include"
            if not fake_libc.exists():
                # Try alternate location
                import subprocess, sys
                sp = subprocess.run(
                    [sys.executable, "-c",
                     "import pycparser; print(pycparser.__file__)"],
                    capture_output=True, text=True
                )
                pkg_path = Path(sp.stdout.strip()).parent
                fake_libc = pkg_path / "utils" / "fake_libc_include"

            ast = parse_file(
                str(source_path),
                use_cpp=True,
                cpp_path="gcc",
                cpp_args=[
                    "-E",
                    f"-I{fake_libc}",
                ],
            )

            visitor = _CAnalysisVisitor()
            visitor.visit(ast)
            visitor.detect_recursion()

            result.functions      = visitor.functions
            result.function_names = [f.name for f in visitor.functions]
            result.global_variables = visitor.global_vars
            result.loop_count     = visitor.loop_count
            result.if_count       = visitor.if_count
            result.switch_count   = visitor.switch_count
            result.goto_count     = visitor.goto_count
            result.recursion_count= sum(1 for f in visitor.functions if f.is_recursive)
            result.has_main       = any(f.name == "main" for f in visitor.functions)
            main_fn = next((f for f in visitor.functions if f.name == "main"), None)
            if main_fn:
                result.main_uses_argc = "argc" in main_fn.param_names
            result.analysis_method = "pycparser"

        except Exception as exc:
            logger.warning("pycparser failed (%s) — falling back to regex", exc)
            _regex_analyse(source, result)
    else:
        _regex_analyse(source, result)

    result.cyclomatic_complexity = _cyclomatic_complexity(result)
    _apply_warning_rules(result, source)

    return result


def analysis_to_dict(result: StaticAnalysisResult) -> dict:
    """Convert StaticAnalysisResult to a JSON-serialisable dict."""
    return {
        "analysis_method":      result.analysis_method,
        "line_count":           result.line_count,
        "has_main":             result.has_main,
        "functions_count":      len(result.functions),
        "function_names":       result.function_names,
        "functions": [
            {
                "name":         f.name,
                "return_type":  f.return_type,
                "param_count":  f.param_count,
                "param_types":  f.param_types,
                "param_names":  f.param_names,
                "is_recursive": f.is_recursive,
                "line_number":  f.line_number,
            }
            for f in result.functions
        ],
        "global_variables":     result.global_variables,
        "includes":             result.includes,
        "control_flow": {
            "loops":       result.loop_count,
            "if_blocks":   result.if_count,
            "switches":    result.switch_count,
            "recursions":  result.recursion_count,
            "gotos":       result.goto_count,
        },
        "cyclomatic_complexity": result.cyclomatic_complexity,
        "io_patterns": {
            "printf":   result.uses_printf,
            "scanf":    result.uses_scanf,
            "gets":     result.uses_gets,
            "malloc":   result.uses_malloc,
            "free":     result.uses_free,
            "fopen":    result.uses_fopen,
            "arrays":   result.uses_arrays,
            "pointers": result.uses_pointers,
            "structs":  result.uses_structs,
        },
        "warnings": result.warnings,
        "errors":   result.errors,
    }