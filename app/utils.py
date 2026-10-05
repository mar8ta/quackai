"""
app/utils.py

Shared helper functions used across the app package.
"""

import re


def clean_input(text: str) -> str:
    """Normalize raw user input before we analyze it.

    - Strips leading/trailing whitespace.
    - Collapses any run of internal whitespace (spaces, tabs, newlines)
      into a single space.

    This does NOT remove or alter any meaningful characters — it only
    tidies up whitespace so the rules in validator.py can rely on
    consistent spacing.
    """
    if text is None:
        return ""
    return re.sub(r"\s+", " ", text.strip())
