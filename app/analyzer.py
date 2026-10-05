"""
app/analyzer.py

Orchestrates the analysis pipeline:

    User Input
       -> clean
       -> classify input TYPE (Phase 4)
       -> validate (rule-based, Phase 2)
       -> validate (math/SymPy, Phase 3)
       -> validate (type-aware checks, Phase 4)
       -> [knowledge base + AI layer in later phases]

The input TYPE is determined once, up front, and attached to every
possible response — whether the problem was caught by the generic
structural rules, the math parser, or a type-aware check, the caller
always learns both WHAT kind of input it was and WHAT (if anything)
was wrong with it. These two pieces of information are kept as
separate fields the whole way through, per the project's INPUT TYPE /
INPUT STATUS distinction.
"""

from app.utils import clean_input
from app.validator import validate_basic
from app.math_validator import validate_math_expression
from app.classifier import classify_input


def analyze_input(raw_input: str) -> dict:
    """Run the full (current) analysis pipeline on a piece of raw user
    input and return a plain dict matching the AnalyzeResponse shape.
    """
    cleaned = clean_input(raw_input)

    classification = classify_input(cleaned)
    input_type = classification.input_type

    problem = validate_basic(cleaned)
    if problem is not None:
        return _with_type(problem.to_dict(), input_type)

    problem = validate_math_expression(cleaned)
    if problem is not None:
        return _with_type(problem.to_dict(), input_type)

    if classification.problem is not None:
        return _with_type(classification.problem.to_dict(), input_type)

    return _with_type(
        {
            "status": "valid",
            "category": "unclassified",
            "message": "No structural, mathematical, or type-specific problems detected. (Knowledge-base explanations and the AI/NLP layer arrive in later phases.)",
            "suggestion": None,
        },
        input_type,
    )


def _with_type(result: dict, input_type: str) -> dict:
    """Attach the classified input type to a result dict without
    disturbing its other fields."""
    result["type"] = input_type
    return result