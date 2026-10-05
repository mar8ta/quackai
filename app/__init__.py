"""
app package

This package holds the core "brain" of QuackAI:
- analyzer.py       -> orchestrates the analysis pipeline
- classifier.py      -> figures out input type and input status
- validator.py        -> deterministic rule-based validation
- explainer.py        -> turns a detected problem into a human-friendly message
- knowledge_base.py    -> loads/queries the error-pattern knowledge base
- utils.py             -> shared helper functions

These are intentionally created as empty stubs in Phase 1. We implement
them one at a time in the phases that follow, so each piece can be
tested in isolation before we wire it all together.
"""
