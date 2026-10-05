# QuackAI 🦆

*"Let's find the problem."*

An intelligent input-validation and error-explanation system.

QuackAI detects when a user's input — a math expression, a statistics
question, a logical statement, or a natural-language request — is
invalid, contradictory, ambiguous, or incomplete. Instead of guessing
at an answer or hallucinating a response, it explains **what's wrong**
in plain language and suggests a correction.

This is not a chatbot that answers everything. Its job is to ask:
*"Is this input understandable, logically consistent, complete and
valid enough to process?"* — and only proceed if the answer is yes.

## Status: Phase 3 of 12 complete

| Phase | What it adds | Status |
|---|---|---|
| 1 | Project skeleton + running FastAPI app | ✅ Done |
| 2 | Deterministic, rule-based validation | ✅ Done |
| 3 | Mathematical validation with SymPy | ✅ Done |
| 4 | Input type + input status classification | ⏳ Next |
| 5 | Expandable knowledge base of error patterns | Planned |
| 6 | NLP/AI interpretation layer | Planned |
| 7 | Web frontend | Planned |
| 8 | Frontend/backend integration | Planned |
| 9 | Automated test suite | Planned |
| 10 | Security hardening | Planned |
| 11 | UI/UX polish | Planned |
| 12 | Documentation + deployment | Planned |

`POST /analyze` now runs deterministic structural checks AND real
symbolic math validation (division by zero, indeterminate forms,
expressions SymPy's grammar rejects). It does not yet classify input
type (Phase 4) or use an AI layer for natural language (Phase 6).

## How it works (current pipeline)

```
User Input
   │
   ▼
clean_input()             # app/utils.py         — normalize whitespace
   │
   ▼
validate_basic()          # app/validator.py       — rule-based structural checks
   │
   ▼
validate_math_expression() # app/math_validator.py — SymPy symbolic parsing
   │
   ▼
AnalyzeResponse             # status, category, message, suggestion
```

Future phases extend this pipeline with type classification, a
knowledge base of explanations, and an AI/NLP layer for natural
language input — without changing this basic shape.

## What's actually detected right now

These are deterministic, rule-based checks — no AI, no `eval()`, just
careful string and regex inspection. Checks run in order and stop at
the first problem found.

| # | Check | Example input | `status` | `category` |
|---|---|---|---|---|
| 1 | Empty input | `""` | `incomplete` | `empty_input` |
| 2 | Unsupported characters | `"2 + 3 😀"` | `unsupported` | `unsupported_characters` |
| 3 | Unbalanced parentheses | `"(2 + 3"` | `invalid` | `unbalanced_parentheses` |
| 4 | Consecutive operators | `"2 + * 3"` | `invalid` | `invalid_operator_sequence` |
| 5 | Invalid leading operator | `"* 3 + 2"` | `invalid` | `invalid_start` |
| 6 | Trailing operator | `"2 +"` | `incomplete` | `incomplete_expression` |
| 7 | Division by zero | `"5 / 0"` | `invalid` | `division_by_zero` |
| 8 | Indeterminate form | `"0 / 0"` | `invalid` | `indeterminate_form` |
| 9 | Malformed math syntax | `"x === 2"` | `invalid` | `malformed_expression` |
| 10 | Code-injection-like syntax | `"eval(2+2)"` | `unsupported` | `unsupported_syntax` |

Checks 1–6 (Phase 2) are plain regex/string rules. Checks 7–10
(Phase 3) come from actually parsing the expression with SymPy's
symbolic engine — see `app/math_validator.py` for the security notes
on how that parser is sandboxed.

If none of these fire, the input currently passes through as `valid`
(type classification and logic validation are Phase 4+).

The system distinguishes two separate ideas, kept intentionally apart
in the architecture (`app/classifier.py`, arriving Phase 4):

- **Input type** — what *kind* of input it is (math, calculus,
  statistics, logic, natural language, ...).
- **Input status** — what's *wrong* with it, if anything (valid,
  invalid, ambiguous, contradictory, incomplete, unsupported).

## Project structure

```
quackai/
├── app/                     # Core analysis logic
│   ├── analyzer.py            # orchestrates the pipeline
│   ├── validator.py            # structural rule-based checks (Phase 2 ✅)
│   ├── math_validator.py        # SymPy symbolic math validation (Phase 3 ✅)
│   ├── utils.py                 # input cleanup helpers (Phase 2 ✅)
│   ├── classifier.py              # input type/status classification (Phase 4)
│   ├── explainer.py                # knowledge-base-driven explanations (Phase 5)
│   └── knowledge_base.py            # error-pattern lookup (Phase 5)
├── api/
│   └── routes.py             # FastAPI endpoints: GET /health, POST /analyze
├── frontend/                  # Web UI — built in Phase 7
├── tests/                       # Automated tests — built in Phase 9
├── data/
│   └── knowledge_base.json       # error-pattern database — populated in Phase 5
├── requirements.txt
├── config.py                   # settings, loaded from environment variables
├── run.py                      # entry point — run this file
└── README.md
```

## Setup

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
python run.py
```

Then open:
- http://127.0.0.1:8000/ — root status message
- http://127.0.0.1:8000/docs — interactive API docs (Swagger UI)

## Try it

```bash
curl -X POST http://127.0.0.1:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"input": "2 +"}'
```

Response:

```json
{
  "status": "incomplete",
  "category": "incomplete_expression",
  "message": "Your expression appears incomplete. It ends with an operator, but there is no value after it.",
  "suggestion": "Try adding a value after the operator, e.g. 2 + 3."
}
```

A few more to try:

```bash
curl -X POST http://127.0.0.1:8000/analyze -H "Content-Type: application/json" -d '{"input": "2 + 3"}'
curl -X POST http://127.0.0.1:8000/analyze -H "Content-Type: application/json" -d '{"input": "(2 + 3"}'
curl -X POST http://127.0.0.1:8000/analyze -H "Content-Type: application/json" -d '{"input": "* 3 + 2"}'
curl -X POST http://127.0.0.1:8000/analyze -H "Content-Type: application/json" -d '{"input": ""}'
```

## Design principles

- **No `eval()`, ever.** User input is never executed as code, on any
  path, in any phase. SymPy's own parser uses `eval()` internally, so
  it's sandboxed with a restricted namespace (`__builtins__` explicitly
  emptied) plus a denylist checked before parsing even starts — see
  the security notes at the top of `app/math_validator.py`.
- **Deterministic checks first.** Rule-based validation is fast, cheap,
  and predictable. The AI/NLP layer (Phase 6) is reserved for cases
  that genuinely require language understanding — it is not the first
  line of defense.
- **Explain, don't guess.** When input is ambiguous, contradictory, or
  incomplete, QuackAI says so and suggests a fix rather than producing
  a best-effort (and possibly wrong) answer.
- **Secrets stay in environment variables.** See `.env.example` — API
  keys are never hard-coded.

## Tech stack (so far)

- **Python 3.11+**
- **FastAPI** — REST API framework
- **Pydantic** — request/response validation
- **python-dotenv** — environment-based configuration
- **SymPy** — symbolic math parsing and validation

NumPy and pandas are added when statistics-specific validation is
built; an AI/NLP integration is added in Phase 6.
