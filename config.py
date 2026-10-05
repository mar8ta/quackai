"""
config.py

Central place for application configuration.

We load settings from environment variables (and an optional .env file)
instead of hard-coding them. This keeps secrets like API keys out of
the source code, which we will rely on more heavily starting Phase 6
(NLP/AI layer).
"""

import os
from dotenv import load_dotenv

# Load variables from a .env file into the environment, if one exists.
# This is safe to call even if no .env file is present.
load_dotenv()


class Settings:
    """Simple settings container. Values come from environment variables,
    with sensible defaults for local development.
    """

    # --- App metadata ---
    APP_NAME: str = "QuackAI"
    APP_VERSION: str = "0.1.0"

    # --- Server ---
    HOST: str = os.getenv("QUACKAI_HOST", "127.0.0.1")
    PORT: int = int(os.getenv("QUACKAI_PORT", "8000"))
    DEBUG: bool = os.getenv("QUACKAI_DEBUG", "true").lower() == "true"

    # --- AI / NLP layer (used from Phase 6 onward) ---
    OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")

    # --- Limits (used from Phase 10 onward) ---
    MAX_INPUT_LENGTH: int = int(os.getenv("QUACKAI_MAX_INPUT_LENGTH", "2000"))


settings = Settings()
