"""
app/classifier.py

Phase 4: input classification along two SEPARATE axes.

    INPUT TYPE   -> what kind of input this is
                    (mathematics | calculus | statistics | logic |
                     natural_language | general_question | unknown)

    INPUT STATUS -> what's wrong with it, if anything
                    (valid | invalid | ambiguous | contradictory |
                     incomplete | unsupported)

These are kept conceptually distinct on purpose: knowing an input is
"statistics" doesn't tell you whether it's valid, and knowing an input
is "incomplete" doesn't tell you whether it was math or a logic
statement. ClassificationResult below always carries both.

This module determines TYPE with keyword/pattern heuristics (good
enough for now; Phase 6's AI layer will handle genuinely ambiguous
cases). It also runs a small number of TYPE-AWARE status checks that
only make sense once we know the domain — e.g. checking a dataset for
non-numeric values only makes sense once we know we're looking at
statistics input. These checks are intentionally narrow, hand-picked
examples, not general-purpose engines:

    - statistics: flags non-numeric values in an explicit dataset
      (e.g. "Find the mean of 4, 6, 8, banana, 10")
    - statistics: flags a specific, well-known contradiction pattern
      (asking for the probability of a standard die showing a value
      it cannot show)
    - calculus: flags a calculus request with no expression attached
      (e.g. "What's the derivative?")

Broader contradiction/ambiguity detection across all domains is the
job of the knowledge base (Phase 5) and the AI/NLP layer (Phase 6).
"""

import re
from dataclasses import dataclass
from typing import Optional

import pandas as pd

from app.validator import ValidationResult

VALID_INPUT_TYPES = {
    "mathematics",
    "calculus",
    "statistics",
    "logic",
    "natural_language",
    "general_question",
    "unknown",
}


@dataclass
class ClassificationResult:
    """Carries BOTH axes explicitly, so callers never confuse one for
    the other.

    input_type: one of VALID_INPUT_TYPES.
    problem:    a ValidationResult if a type-aware check found a
                problem, or None if classification found nothing wrong
                (the general validators may still flag something, or
                the input may simply be valid).
    """

    input_type: str
    problem: Optional[ValidationResult] = None


# ---------------------------------------------------------------------
# Input TYPE detection
# ---------------------------------------------------------------------

# Logic connective symbols count as a strong, unambiguous signal.
_LOGIC_SYMBOLS = re.compile(r"[∧∨¬→↔⇒⇔⊢⊨]")
_IF_THEN_PATTERN = re.compile(r"\bif\b.+\bthen\b", re.IGNORECASE)
_LOGIC_TERMS = re.compile(
    r"\b(proposition|syllogism|contradiction|logically|premise|tautology|"
    r"therefore|iff|biconditional)\b",
    re.IGNORECASE,
)

_CALCULUS_TERMS = re.compile(
    r"\b(derivative|differentiate|differentiation|integral|integrate|"
    r"integration|antiderivative|limit|d/dx|lim)\b",
    re.IGNORECASE,
)

_STATISTICS_TERMS = re.compile(
    r"\b(mean|average|median|mode|standard deviation|variance|probability|"
    r"dataset|distribution|correlation|regression|sample|population|"
    r"percentile|dice|die|coin)\b",
    re.IGNORECASE,
)

_WH_WORD = re.compile(r"\b(what|how|why|who|when|where|which)\b", re.IGNORECASE)

# Characters that suggest "this is raw math notation" rather than prose.
_EXPRESSION_CHARS = re.compile(r"[0-9]|[+\-*/^=]")

_COMMON_STOPWORDS = {
    "the", "a", "an", "is", "are", "of", "to", "in", "on", "for", "and",
    "or", "but", "with", "this", "that", "please", "me", "my", "you",
    "your", "about", "tell", "explain",
}


def classify_input_type(text: str) -> str:
    """Determine the INPUT TYPE of `text` using keyword/pattern
    heuristics. Checked in order from most to least specific, so a
    sentence that happens to contain a math symbol but is clearly
    asking a calculus question is still classified as calculus, etc.
    """
    if not text:
        return "unknown"

    if _LOGIC_SYMBOLS.search(text) or _IF_THEN_PATTERN.search(text) or _LOGIC_TERMS.search(text):
        return "logic"

    if _CALCULUS_TERMS.search(text):
        return "calculus"

    if _STATISTICS_TERMS.search(text):
        return "statistics"

    words = re.findall(r"[a-zA-Z]+", text.lower())
    stopword_count = sum(1 for w in words if w in _COMMON_STOPWORDS)

    # Looks like raw math notation: has digits/operators and isn't
    # dominated by ordinary English words.
    if _EXPRESSION_CHARS.search(text) and stopword_count < 2:
        return "mathematics"

    if text.rstrip().endswith("?") and _WH_WORD.search(text):
        return "general_question"

    if len(words) >= 3:
        return "natural_language"

    return "unknown"


# ---------------------------------------------------------------------
# Type-aware status checks
# ---------------------------------------------------------------------

# Matches "mean of X, Y, Z", "average of X, Y", etc. — the specific
# phrasing used to introduce an explicit dataset in a sentence.
_DATASET_PATTERN = re.compile(
    r"\b(?:mean|average|median|mode|sum|total)\s+of\s+(.+)", re.IGNORECASE
)


def _check_statistics_issues(text: str) -> Optional[ValidationResult]:
    """Narrow, type-aware checks for statistics input."""

    # --- Specific contradiction: a die showing a value it cannot show ---
    die_match = re.search(r"(six[- ]sided|6[- ]sided)\s+die", text, re.IGNORECASE)
    if die_match:
        threshold_match = re.search(
            r"(?:greater than|more than|above|over)\s+(\d+)", text, re.IGNORECASE
        )
        if threshold_match and int(threshold_match.group(1)) >= 6:
            return ValidationResult(
                status="contradictory",
                category="contradictory_probability",
                message=(
                    "This request contains a contradiction. A standard six-sided die "
                    "has outcomes from 1 to 6, so there is no outcome greater than "
                    f"{threshold_match.group(1)}. Therefore, the probability is 0."
                ),
                suggestion="Try asking about a value between 1 and 6, e.g. 'greater than 4'.",
            )

    # --- Non-numeric values in an explicit dataset ---
    dataset_match = _DATASET_PATTERN.search(text)
    if dataset_match:
        raw_list = dataset_match.group(1)
        # Trim a trailing question mark/period, and normalize "x and y"
        # into "x, y" so the last item splits out correctly too.
        raw_list = raw_list.rstrip("?. ").replace(" and ", ", ")
        tokens = [t.strip() for t in raw_list.split(",") if t.strip()]

        if tokens:
            numeric = pd.to_numeric(pd.Series(tokens), errors="coerce")
            bad_tokens = [t for t, n in zip(tokens, numeric) if pd.isna(n)]
            if bad_tokens:
                shown = ", ".join(repr(t) for t in bad_tokens)
                return ValidationResult(
                    status="invalid",
                    category="non_numeric_data",
                    message=f"The dataset contains {shown}, which is not a numerical value.",
                    suggestion=f"If {bad_tokens[0]!r} was entered accidentally, replace it with a number.",
                )

    return None


def _check_calculus_issues(text: str) -> Optional[ValidationResult]:
    """Narrow, type-aware check: a calculus request with no actual
    expression attached to work on."""
    if not _EXPRESSION_CHARS.search(text) and "(" not in text:
        return ValidationResult(
            status="incomplete",
            category="missing_expression",
            message="This request is incomplete. Please provide the expression you want differentiated or integrated.",
            suggestion="For example: Find the derivative of x^2 + 3x.",
        )
    return None


def classify_input(text: str) -> ClassificationResult:
    """Classify `text` along both axes. Determines INPUT TYPE first,
    then runs any type-aware status check that applies to that type.

    Always returns a ClassificationResult with input_type set; problem
    is None when no type-aware check found anything wrong (the input
    may still be flagged by the general validators, or may simply be
    valid).
    """
    input_type = classify_input_type(text)

    problem: Optional[ValidationResult] = None
    if input_type == "statistics":
        problem = _check_statistics_issues(text)
    elif input_type == "calculus":
        problem = _check_calculus_issues(text)

    return ClassificationResult(input_type=input_type, problem=problem)