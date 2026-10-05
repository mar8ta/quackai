"""
run.py

Entry point for QuackAI. Creates the FastAPI application, wires in the
API routes, and (when run directly) starts a local development server
with uvicorn.

Usage:
    python run.py
or:
    uvicorn run:app --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from api.routes import router as api_router

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="An intelligent input-validation and error-explanation system.",
)

# Allow the frontend (served separately, e.g. opened as a local HTML file
# or from a different port) to call this API during development.
# We tighten this up in Phase 10 (security hardening).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/")
def root():
    """Root endpoint, just to confirm the API is alive when visited in a browser."""
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "message": "QuackAI API is running. See /docs for the interactive API docs.",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("run:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
