"""
api/routes.py

Defines the HTTP endpoints for QuackAI.

Phase 1 scope:
    - GET  /health   -> simple liveness check
    - POST /analyze  -> placeholder that calls the (stub) analysis
                         pipeline and returns its result

The request/response shapes defined here (AnalyzeRequest, AnalyzeResponse)
are the actual API contract the frontend will use later, so we define
them properly now even though the underlying logic is still a stub.
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.analyzer import analyze_input

router = APIRouter()


class AnalyzeRequest(BaseModel):
    """What the client sends us."""

    input: str = Field(..., description="The raw user input to analyze.")


class AnalyzeResponse(BaseModel):
    """What we send back to the client."""

    status: str = Field(..., description="valid | invalid | ambiguous | contradictory | incomplete | unsupported | unknown")
    category: str = Field(..., description="Problem category, e.g. 'incomplete_expression'.")
    message: str = Field(..., description="Human-readable explanation of the result.")
    suggestion: str | None = Field(None, description="A suggested correction, if any.")


@router.get("/health")
def health_check():
    """Basic liveness check so we can confirm the server is running."""
    return {"status": "ok", "service": "QuackAI"}


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest):
    """Analyze a piece of user input.

    Phase 1: delegates to the stub `analyze_input`, which always returns
    a fixed placeholder result. Real validation/classification logic is
    added in the phases that follow.
    """
    result = analyze_input(request.input)
    return result
