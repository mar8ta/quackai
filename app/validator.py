"""
app/validator.py

Deterministic, rule-based validation. These checks are fast, predictable,
and require no AI/NLP or symbolic math — they catch obvious structural
problems (empty input, dangling operators, unbalanced parentheses, etc.)
before we spend effort on heavier analysis in later phases.

Important: this module never calls eval() or executes user input as
code. All checks are done with plain string inspection and regular
expressions.
"""

import re
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class ValidationResult:
    """The outcome of a validation check.

    status:   one of "valid" | "invalid" | "ambiguous" | "contradictory"
              | "incomplete" | "unsupported"
    category: a short machine-readable label, e.g. "incomplete_expression".
              These labels are the keys we'll look up in the knowledge
              base starting in Phase 5.
    message:      human-readable explanation of what is wrong.
    suggestion:   an optional suggested correction.
    """

    status: str
    category: str
    message: str
    suggestion: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


# Characters we consider "safe" for the kinds of input QuackAI expects
# right now (math-like expressions and plain English text). Anything
# outside this set (emoji, control characters, stray symbols like # $ ~)
# gets flagged rather than silently processed.
_ALLOWED_CHAR_RE = re.compile(r"[a-zA-Z0-9\s\+\-\*/\^%\(\)\.\,\=\<\>\!\?\_\'\"]")

# Operator characters used by the structural checks below.
_OPERATOR_CHARS = r"+\-*/^%"

# Multi-character operator tokens that are valid and should NOT be
# flagged by the "consecutive operators" check.
_ALLOWED_OPERATOR_RUNS = {"**", "//"}


def _find_unsupported_characters(text: str) -> list[str]:
    """Return the sorted list of distinct characters in `text` that are
    not in our allowed set."""
    bad = {ch for ch in text if not _ALLOWED_CHAR_RE.fullmatch(ch)}
    return sorted(bad)


def _has_balanced_parentheses(text: str) -> bool:
    """Check that every '(' has a matching ')' and they're never closed
    before they're opened."""
    depth = 0
    for ch in text:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0


def _find_consecutive_operator_run(text: str) -> Optional[str]:
    """Find two or more operators in a row, optionally separated by
    whitespace (e.g. "2 +* 3" and "2 + * 3" are both caught), that
    together aren't one of the recognized multi-character operators
    (** or //, written with no space between them)."""
    for match in re.finditer(rf"[{_OPERATOR_CHARS}](?:\s*[{_OPERATOR_CHARS}])+", text):
        run = match.group()
        compact = run.replace(" ", "")
        if compact in _ALLOWED_OPERATOR_RUNS and " " not in run:
            continue
        return run
    return None


def _has_invalid_leading_operator(text: str) -> bool:
    """A leading '+' or '-' is fine (unary sign, e.g. '-3 + 2'), but a
    leading '*', '/', '^' or '%' can never start a valid expression."""
    first = text.lstrip()[:1]
    return first in {"*", "/", "^", "%"}


def _has_trailing_operator(text: str) -> bool:
    """True if the input ends with an operator (or '='), meaning
    something is clearly expected to follow but doesn't."""
    last = text.rstrip()[-1:]
    return last in set(_OPERATOR_CHARS.replace("\\", "")) | {"="}


def validate_basic(text: str) -> Optional[ValidationResult]:
    """Run all deterministic rule-based checks on `text`.

    Returns a ValidationResult describing the first problem found, or
    None if the input passes every basic structural check (this does
    NOT mean the input is fully valid — deeper math/logic validation
    happens in later phases).

    Checks run in this order, stopping at the first match:
        1. Empty input
        2. Unsupported characters
        3. Unbalanced parentheses
        4. Consecutive operators (e.g. "2 + * 3")
        5. Invalid leading operator (e.g. "* 3 + 2")
        6. Trailing operator (e.g. "2 +")
    """
    if not text:
        return ValidationResult(
            status="incomplete",
            category="empty_input",
            message="You haven't entered anything yet. Please type a question or expression to analyze.",
            suggestion="Try something like: 2 + 3",
        )

    bad_chars = _find_unsupported_characters(text)
    if bad_chars:
        shown = ", ".join(repr(c) for c in bad_chars[:5])
        return ValidationResult(
            status="unsupported",
            category="unsupported_characters",
            message=f"Your input contains character(s) QuackAI doesn't support yet: {shown}.",
            suggestion="Remove or replace these characters and try again.",
        )

    if not _has_balanced_parentheses(text):
        return ValidationResult(
            status="invalid",
            category="unbalanced_parentheses",
            message="Your expression has unbalanced parentheses — an opening '(' without a matching ')', or vice versa.",
            suggestion="Check that every '(' has a matching ')'.",
        )

    bad_run = _find_consecutive_operator_run(text)
    if bad_run:
        return ValidationResult(
            status="invalid",
            category="invalid_operator_sequence",
            message=f"Your expression has two or more operators in a row ('{bad_run}'), which isn't valid.",
            suggestion="Make sure exactly one operator separates each pair of values.",
        )

    if _has_invalid_leading_operator(text):
        return ValidationResult(
            status="invalid",
            category="invalid_start",
            message="Your expression starts with an operator that requires a value before it.",
            suggestion="Start with a number or variable, e.g. 2 * 3 instead of * 3.",
        )

    if _has_trailing_operator(text):
        return ValidationResult(
            status="incomplete",
            category="incomplete_expression",
            message="Your expression appears incomplete. It ends with an operator, but there is no value after it.",
            suggestion="Try adding a value after the operator, e.g. 2 + 3.",
        )

    return None
