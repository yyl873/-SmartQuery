# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Development
uvicorn app.main:app --reload          # Start dev server on localhost:8000
python init_db.py                      # Seed example database (ecommerce: users, products, orders)

# Testing
pytest tests/ -v                       # Run all 67 tests
pytest tests/test_utils.py -v          # Run only security/encoding tests
pytest tests/test_database.py -v       # Run only CSV/database tests

# Packaging
pyinstaller smartquery.spec --clean --noconfirm   # Build Windows EXE → dist/SmartQuery.exe
pip install -r requirements.txt                   # Install all deps

# Docker
docker compose up -d                    # Start with Docker
```

## Architecture

**Backend**: FastAPI app (`app/main.py`) — 18 endpoints. All routes in one file; no separate routers.

**Database layer** (`app/database.py`): SQLAlchemy Core (not ORM). A single global `engine` variable supports runtime switching between SQLite/MySQL/PostgreSQL via `reconnect()`. Schema extraction uses `sqlalchemy.inspect`. CSV import auto-detects delimiter (via `csv.Sniffer`) and encoding (tries UTF-8 BOM → UTF-16 BOM → UTF-8 → GBK → GB18030).

**LLM layer** (`app/llm.py`): OpenAI-compatible client (works with DeepSeek/GPT). Key design decisions:
- Messages use **only `user` role** — no `system` messages (DeepSeek requirement)
- `temperature=0` for deterministic SQL generation
- `_match_fewshot()` selects relevant examples from a hardcoded 8-example library based on keyword overlap — no vector DB needed
- `generate_sql_stream()` yields tokens for SSE endpoint
- Auto-retry: 1 retry on timeout/API error with 1.5s delay

**SQL safety** (`app/utils.py`): Two-tier model using **sqlparse AST token analysis** (not regex):
- Default (`write_mode=False`): blocks DROP, ALTER, TRUNCATE, CREATE, GRANT, REVOKE, DELETE, UPDATE, INSERT
- Write mode (`write_mode=True`): allows DELETE/UPDATE/INSERT, still blocks DDL
- Checks token types (`Keyword.DDL`, `Keyword.DML`) to avoid flagging string literals like `SELECT 'drop it'`
- Falls back to substring matching if sqlparse fails

**Frontend** (`app/static/index.html`): Single 52KB HTML file — no frameworks. Glassmorphism CSS with `backdrop-filter: blur()`, CSS custom properties for light/dark theming. Three persona modes (pro/normal/simple) controlled by body class `mode-normal` toggling `.pro-only` elements via `display:none !important`. All destructive actions (delete table, disconnect, write mode) require confirmation dialogs. Write mode checkbox passes `write_mode: true` in the `/query` request body.

## Key patterns

- **CSV import flow**: read bytes → `detect_encoding()` → decode → `_detect_delimiter()` → create table with `_guess_type()` on sample values → INSERT rows
- **Query flow**: receive question → `get_schema()` → `generate_sql()` (with few-shot) → `is_safe_sql()` check → `execute_sql()` → on failure, `fix_sql()` retry once → `generate_translation()` for zh/en explanations
- **DB switching**: `reconnect()` disposes old engine, builds URL via `_build_url()`, creates new engine. SQLite uses `sqlite:///./path`, MySQL uses `mysql+pymysql://`, PG uses `postgresql://`.
- **Persona persistence**: stored in `localStorage('smartquery-persona')`. Simple mode is NOT persisted (user can re-choose). `mode-normal` body class hides `.pro-only` elements.
- **Frontend state**: `currentSQL`, `currentData`, `currentPage` (50 rows/page), `MAX_HISTORY=20` in localStorage

## Environment

Copy `.env.example` to `.env` and configure:
- `LLM_API_KEY` — required for SQL generation
- `LLM_BASE_URL` — defaults to OpenAI, commonly set to `https://api.deepseek.com`
- `LLM_MODEL` — e.g. `deepseek-chat`
- `DATABASE_URL` — optional, defaults to SQLite

## Tests

67 tests in `tests/` covering: `is_safe_sql()` all modes + edge cases (multi-statement, string literals, empty/whitespace), `is_safe_table_name()`, `detect_encoding()` all codecs + BOM, `format_sql()`, `_detect_delimiter()`, `_guess_type()`, `_build_url()`. Uses `is` comparison for SQLAlchemy types (they're classes, not strings).
