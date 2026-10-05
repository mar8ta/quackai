"""
app/analyzer.py

Orchestrates the analysis pipeline:

    User Input -> clean -> validate (rule-based) -> validate (math/SymPy) -> [more phases later]

Phase 3 scope: after the deterministic structural checks in
validator.py pass, we hand the input to math_validator.py, which
attempts a real symbolic parse with SymPy. This catches problems
regex alone can't see (e.g. division by zero, expressions SymPy's
grammar rejects). Type classification (Phase 4), knowledge-base-driven
explanations (Phase 5), and the AI/NLP layer (Phase 6) all plug in
here in later phases.
"""

from app.utils import clean_input
from app.validator import validate_basic
from app.math_validator import validate_math_expression


def analyze_input(raw_input: str) -> dict:
    """Run the full (current) analysis pipeline on a piece of raw user
    input and return a plain dict matching the AnalyzeResponse shape.
    """
    cleaned = clean_input(raw_input)

    problem = validate_basic(cleaned)
    if problem is not None:
        return problem.to_dict()

    problem = validate_math_expression(cleaned)
    if problem is not None:
        return problem.to_dict()

    return {
        "status": "valid",
        "category": "unclassified",
        "message": "No structural or mathematical problems detected. (Type classification and deeper logical validation arrive in later phases.)",
        "suggestion": None,
    }
