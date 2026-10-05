"""
app/math_validator.py

Phase 3: mathematical validation using SymPy.

Goes beyond the structural checks in validator.py by actually parsing
mathematical expressions with SymPy's symbolic engine. This catches
things plain regex cannot, such as:
    - expressions SymPy's grammar rejects outright ("sin(x", "x === 2")
    - division by zero ("5 / 0" -> ComplexInfinity)
    - indeterminate forms ("0 / 0" -> NaN)

SECURITY NOTE — read before touching this file:
SymPy's `parse_expr` uses Python's `eval()` internally on a
token-transformed version of the input string. Left unguarded, that is
a code-execution risk (e.g. a crafted string that resolves to
`__import__('os')`). We mitigate this with two independent layers:

  1. A denylist checked BEFORE we ever call the parser, on every
     input regardless of whether it looks like math. It flags dunder
     attribute access (`__class__`, `__import__`, ...) anywhere, the
     bare keywords `import`/`lambda`, and call-like patterns such as
     `eval(`, `exec(`, `open(`, `os(`, `system(`, `subprocess(`,
     `compile(`, `globals(`, `locals(`, `input(`. Dangerous words are
     only flagged when they look like a function call (followed by
     "("); an earlier version matched them as plain substrings and
     falsely flagged ordinary input like "evaluate this expression"
     (contains "eval") and "system of equations" (contains "system").
  2. The parser is given a restricted global namespace containing only
     SymPy's own names, with `__builtins__` explicitly set to an empty
     dict. This stops Python's `eval()` from silently falling back to
     the real builtins module — which it does automatically whenever
     `__builtins__` is absent from the globals dict passed to it.

Both layers were manually verified against real injection attempts
(`__import__('os').system(...)`, `open('/etc/passwd')`, attribute-chain
tricks) during development — none resulted in code execution.

We never call Python's built-in eval() directly anywhere in this file
or project.
"""

import re
from tokenize import TokenError
from typing import Optional

from sympy import nan, zoo
from sympy import SympifyError
from sympy.parsing.sympy_parser import (
    parse_expr,
    standard_transformations,
    implicit_multiplication_application,
    convert_xor,
)

from app.validator import ValidationResult

_TRANSFORMATIONS = standard_transformations + (
    implicit_multiplication_application,
    convert_xor,
)

# --- Security layer 1: denylist checked before parsing ---
# We deliberately require dangerous words to be followed by "(" (i.e.
# look like a function call) before flagging them, except for dunder
# names and the bare "import"/"lambda" keywords. An early version of
# this check matched these words as plain substrings, which caused
# false positives on completely ordinary input — "evaluate this
# expression" was flagged because it contains "eval", and "system of
# equations" was flagged because it contains "system". Requiring a
# call-like pattern avoids that while still catching real attempts
# such as "eval(2+2)", "os.system('ls')", or "__import__('os')".
_DUNDER_PATTERN = re.compile(r"__\w+__")
_CALL_LIKE_DENYLIST = re.compile(
    r"\b(import|exec|eval|open|os|system|subprocess|compile|globals|locals|input)\s*\(",
    re.IGNORECASE,
)
_KEYWORD_DENYLIST = re.compile(r"\b(import|lambda)\b", re.IGNORECASE)

# Exceptions SymPy's parser is known to raise on malformed input. These
# vary depending on where in parsing/tokenizing the failure occurs.
_PARSE_FAILURE_EXCEPTIONS = (
    SyntaxError,
    TokenError,
    IndexError,
    TypeError,
    AttributeError,
    ValueError,
    RecursionError,
)

# A lightweight stand-in for real input-type classification (Phase 4).
# These words suggest the input is an English sentence rather than raw
# math notation, so we skip SymPy parsing rather than throw a confusing
# parser error at a sentence. This heuristic is replaced once the
# classifier exists and can make this decision properly.
_SENTENCE_MARKERS = {
    "the", "is", "are", "of", "what", "find", "calculate", "solve",
    "please", "how", "does", "explain", "mean", "probability", "if",
    "when", "who", "why", "derivative", "integral", "a", "an", "for",
}


def _build_safe_global_dict() -> dict:
    """Build a namespace containing only SymPy's own names, with
    __builtins__ explicitly emptied out (security layer 2)."""
    safe_globals: dict = {}
    exec("from sympy import *", safe_globals)  # nosec: fixed, trusted source string, not user input
    safe_globals["__builtins__"] = {}
    return safe_globals


_SAFE_GLOBALS = _build_safe_global_dict()


def _contains_dangerous_syntax(text: str) -> bool:
    """True if `text` contains patterns associated with code injection
    attempts (dunder attribute access, or a call to a
    dangerous-sounding function). Checked on every input, independent
    of whether it looks like a math expression, so a suspicious string
    is never silently reported as 'valid' just because it fails the
    math heuristic below.
    """
    return bool(
        _DUNDER_PATTERN.search(text)
        or _CALL_LIKE_DENYLIST.search(text)
        or _KEYWORD_DENYLIST.search(text)
    )


def _looks_like_math_expression(text: str) -> bool:
    """Heuristic: does this look like math notation worth parsing with
    SymPy, as opposed to an English sentence?

    Intentionally conservative — we'd rather skip a borderline case
    than throw a confusing SymPy error at a natural-language question.
    Superseded by proper classification in Phase 4.
    """
    words = re.findall(r"[a-zA-Z]+", text.lower())
    sentence_word_count = sum(1 for w in words if w in _SENTENCE_MARKERS)
    if sentence_word_count >= 2:
        return False
    if text.rstrip().endswith("?"):
        return False

    has_digit = bool(re.search(r"\d", text))
    has_operator = bool(re.search(r"[+\-*/^%=]", text))
    return has_digit or has_operator


def validate_math_expression(text: str) -> Optional[ValidationResult]:
    """Attempt to parse `text` as a mathematical expression with SymPy
    and translate any problem into a ValidationResult.

    Returns None if:
        - the input doesn't look like math notation (so the pipeline
          can move on to other checks), or
        - it parses cleanly with no mathematical problems.
    """
    if _contains_dangerous_syntax(text):
        return ValidationResult(
            status="unsupported",
            category="unsupported_syntax",
            message="Your input contains terms that aren't supported for mathematical analysis.",
            suggestion="Please enter a plain mathematical expression, e.g. 2 * x + 5.",
        )

    if not _looks_like_math_expression(text):
        return None

    try:
        parsed = parse_expr(
            text,
            transformations=_TRANSFORMATIONS,
            global_dict=_SAFE_GLOBALS,
            local_dict={},
            evaluate=True,
        )
    except ZeroDivisionError:
        return ValidationResult(
            status="invalid",
            category="division_by_zero",
            message="This expression divides by zero, which is undefined in standard arithmetic.",
            suggestion="Check the denominator — division by zero has no defined result.",
        )
    except SympifyError:
        return ValidationResult(
            status="invalid",
            category="malformed_expression",
            message="This doesn't parse as a valid mathematical expression.",
            suggestion="Check for typos, missing operators, or mismatched symbols.",
        )
    except _PARSE_FAILURE_EXCEPTIONS:
        return ValidationResult(
            status="invalid",
            category="malformed_expression",
            message="This doesn't parse as a valid mathematical expression.",
            suggestion="Check for typos, missing operators, unmatched parentheses, or unsupported syntax.",
        )
    except Exception:
        # Catch-all safety net: an unexpected parser error should never
        # crash the request — it should be reported as a problem with
        # the input instead.
        return ValidationResult(
            status="invalid",
            category="malformed_expression",
            message="This doesn't parse as a valid mathematical expression.",
            suggestion="Check for typos, missing operators, unmatched parentheses, or unsupported syntax.",
        )

    if parsed == zoo:
        return ValidationResult(
            status="invalid",
            category="division_by_zero",
            message="This expression divides by zero, which is undefined in standard arithmetic.",
            suggestion="Check the denominator — division by zero has no defined result.",
        )

    if parsed == nan:
        return ValidationResult(
            status="invalid",
            category="indeterminate_form",
            message="This expression evaluates to an indeterminate form (0/0), which has no single defined value.",
            suggestion="Double-check the values involved — 0 divided by 0 is undefined in standard arithmetic.",
        )

    return None
