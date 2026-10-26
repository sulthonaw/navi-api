# AGENTS.md: Developer & AI Agent Guide for Navi Backend

Welcome to the **Navi Backend & API** repository. This document serves as the single source of truth for AI agents (Antigravity, Claude, Cursor, Copilot) and human developers maintaining, extending, or integrating this system.

---

## 1. Project Overview & Philosophy

**Navi** (*Navigate Your Own Code*) is a kiosk-based examination platform for Python programming courses. It prevents cheating by locking down student desktop kiosks, while empowering students through an interactive **Socratic Hint Engine** powered by **Google Gemini**.

### Core Tenets:
1. **100% English Naming Standard**: All folders, files, variables, functions, classes, database tables, columns, Pydantic schemas, and code docstrings **must strictly be written in English**.
2. **Pedagogical Guardrails**: The AI tutor must **never** reveal the code solution, formula, or copy-pasteable code blocks. It must cite the specific line number and ask guiding, reflective questions.
3. **Resilience & Offline Fallbacks**: The server must never crash or return HTTP 500 when external AI APIs or sandbox networks are unavailable. A deterministic heuristic fallback is built into the Socratic engine for offline testing and hackathon demos.
4. **Interactive OpenAPI / Swagger First**: Every endpoint must be documented with Pydantic examples (`json_schema_extra`) so frontend teams (React and Electron) can easily inspect and test the API at `/docs`.

---

## 2. System Architecture

```
navi-api/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/
│   │       │   ├── health.py        # System health & readiness probe
│   │       │   ├── exam_sessions.py # Teacher room & exam management
│   │       │   ├── students.py      # Student room join & status
│   │       │   ├── code.py          # Code run & final submission
│   │       │   ├── hints.py         # Socratic hint requests
│   │       │   ├── violations.py    # Alt+Tab / blur violation reports
│   │       │   └── ws.py            # Real-time WebSocket channels
│   │       └── router.py            # Aggregated v1 API router
│   ├── core/
│   │   ├── config.py                # Pydantic Settings & Swagger metadata
│   │   └── database.py              # Async SQLAlchemy 2.0 engine & session
│   ├── models/
│   │   ├── base.py                  # Declarative base & TimestampMixin
│   │   ├── exam_session.py          # ExamSession & TestCase ORM models
│   │   ├── student_session.py       # StudentSession ORM model
│   │   └── violation_log.py         # ViolationLog ORM model
│   ├── schemas/
│   │   ├── health.py                # Health response schema
│   │   ├── exam_session.py          # Room create, update, response schemas
│   │   ├── student.py               # Student join & status schemas
│   │   ├── code_execution.py        # Code run & test case result schemas
│   │   ├── socratic_hint.py         # Hint request & guidance schemas
│   │   └── violation.py             # Violation report & log schemas
│   ├── services/
│   │   ├── ast_validator.py         # Native Python AST syntax validator
│   │   ├── execution_service.py     # Subprocess sandbox & test runner
│   │   ├── socratic_engine.py       # Google GenAI Gemini engine & guardrails
│   │   ├── websocket_manager.py     # Room-based WebSocket broadcast manager
│   │   └── exam_service.py          # Business logic layer
│   └── main.py                      # FastAPI application entrypoint & OpenAPI
├── scripts/
│   └── export_openapi.py            # Script to export static openapi.json/yaml
├── tests/
│   ├── conftest.py                  # Pytest async SQLite fixtures
│   ├── test_health_and_docs.py      # Health & OpenAPI schema tests
│   ├── test_ast_validator.py        # AST syntax error parsing tests
│   ├── test_execution_service.py    # Code sandbox execution & timeout tests
│   ├── test_socratic_engine.py      # Socratic guardrail & fallback tests
│   └── test_api_flow.py             # Full teacher-student E2E integration tests
├── .dockerignore                    # Docker ignore rules
├── .env.example                     # Environment template
├── Dockerfile                       # Multi-stage container build
├── docker-compose.yml               # PostgreSQL + API container orchestration
├── pyproject.toml                   # Project configuration
├── requirements.txt                 # Pinned dependencies
├── README.md                        # Quickstart documentation
└── AGENTS.md                        # AI agent & developer guidelines (This file)
```

---

## 3. Database & Docker Compose Specifications

### Database Engine
- **Production / Docker**: **PostgreSQL 16** via `asyncpg` driver (`postgresql+asyncpg://navi_user:navi_password@postgres:5432/navi_db`).
- **Development / Tests**: Dynamic support for SQLite via `aiosqlite` (`sqlite+aiosqlite:///:memory:` for lightning-fast pytest runs).

### Docker Compose Services
- `postgres`: PostgreSQL 16 Alpine container with persistent named volume `postgres_data` and automated `pg_isready` healthcheck.
- `navi-api`: FastAPI service with bind mount `./app:/app/app` for live reload, depends on healthy `postgres`.
- `piston-sandbox` *(optional profile: `with-piston`)*: Isolated container for external code execution.

Run containers:
```bash
docker compose up --build
```

---

## 4. API Endpoints Reference

| Tag | Method | Path | Description |
|---|---|---|---|
| **System & Health** | `GET` | `/health` | Top-level health check probe |
| **System & Health** | `GET` | `/api/v1/health` | Detailed service and database ping |
| **System & Health** | `GET` | `/export-openapi` | Download raw OpenAPI 3.1 JSON |
| **Exam Sessions** | `POST` | `/api/v1/rooms` | Teacher creates exam room (generates `room_code`) |
| **Exam Sessions** | `GET` | `/api/v1/rooms/{room_code}` | Get room details and student roster |
| **Exam Sessions** | `PATCH`| `/api/v1/rooms/{room_code}/close` | Conclude exam session |
| **Student Sessions**| `POST` | `/api/v1/students/join` | Student kiosk joins room |
| **Student Sessions**| `GET` | `/api/v1/students/{student_id}` | Query participant status and quota |
| **Code Execution** | `POST` | `/api/v1/code/run` | Run code against public sample test cases |
| **Code Execution** | `POST` | `/api/v1/code/submit` | Final grading against full test suite |
| **Socratic AI** | `POST` | `/api/v1/hints/request` | Request Gemini Socratic hint (decrements quota) |
| **Anti-Cheat** | `POST` | `/api/v1/violations` | Log Alt+Tab / blur event & trigger alarm |
| **WebSockets** | `WS` | `/api/v1/ws/teacher/{room_code}` | Live stream for Teacher Dashboard |
| **WebSockets** | `WS` | `/api/v1/ws/student/{room_code}/{student_id}` | Live stream for Student Kiosk |

---

## 5. WebSocket Event Protocol

When events occur, `WebSocketManager` dispatches JSON payloads to all connected teacher dashboards:

```json
{
  "event": "VIOLATION_DETECTED",
  "room_code": "NAVI-8392",
  "data": {
    "student_id": 1,
    "student_name": "Budi Pratama",
    "student_id_number": "13521001",
    "event_type": "alt_tab",
    "details": "Lost focus to external application",
    "violation_count": 1,
    "timestamp": "2026-10-26T21:40:00Z"
  }
}
```

Registered Events:
- `STUDENT_JOINED`: New student entered the kiosk exam.
- `CODE_STATUS_UPDATED`: Student executed code (status: `tests_passed`, `code_error`, `syntax_error`).
- `HINT_REQUESTED`: Student consumed a hint from their quota.
- `VIOLATION_DETECTED`: Student attempted Alt+Tab / window blur (triggers red highlight & beep alert on teacher screen).
- `EXAM_SUBMITTED`: Student finalized and submitted their exam.
- `EXAM_CLOSED`: Teacher concluded the exam session.

---

## 6. Socratic AI Prompt & Guardrail Rules

When modifying `app/services/socratic_engine.py`:
- Use the official unified Google GenAI SDK: `from google import genai`.
- Keep temperature low (`0.3` - `0.5`) for deterministic, focused pedagogy.
- Guardrails are applied both via system instructions and post-processing regex (`_enforce_guardrails`) to strip any accidental ```python code blocks.
- Preserve the deterministic heuristic fallback (`_generate_heuristic_fallback`) so that local testing and offline demos never fail if an API key is missing.

---

## 7. Testing, Linting & Verification

Run automated tests and code quality linters:
```bash
# Run automated tests
pytest -v

# Run Ruff linter and formatter check
ruff check .
ruff format --check .
```

All 5 test modules must pass with 100% success rate:
1. `tests/test_health_and_docs.py` (Healthcheck & OpenAPI spec verification)
2. `tests/test_ast_validator.py` (AST syntax parsing and line extraction)
3. `tests/test_execution_service.py` (Subprocess runner, stdout/stderr, and timeout handling)
4. `tests/test_socratic_engine.py` (Socratic guardrails, code block stripping, fallback mode)
5. `tests/test_api_flow.py` (End-to-end integration lifecycle)

---

## 8. Guidelines for AI Agents Modifying This Codebase

1. **Do not remove English naming standards**. Keep all variables, functions, and files in English.
2. **Never expose raw database models directly in endpoints**. Always use Pydantic schemas from `app/schemas/`.
3. **Always preserve the AST validator step**. Before running code in the subprocess sandbox, AST validation must execute to immediately capture syntax errors and avoid unnecessary subprocess spawning.
4. **Maintain OpenAPI examples**. When adding or modifying schemas, update `json_schema_extra` with realistic examples so Swagger UI stays interactive.
5. **Enforce Ruff Linting**: Ensure all code passes `ruff check .` and `ruff format --check .` with zero errors.
6. **Use Conventional Commits**: All commit messages must follow the [Conventional Commits](https://www.conventionalcommits.org/) specification (e.g., `feat: ...`, `fix: ...`, `chore: ...`, `docs: ...`, `refactor: ...`).

---

## 9. CI/CD & Self-Hosted Runner Deployment (Mac mini)

The production environment is deployed on an on-premise Mac mini (`vllm-1`) using a self-hosted GitHub Actions runner:

- **Target Directory**: `$HOME/Documents/tendermind/navi-api`
- **Container Architecture**: 100% Docker-based heavy production cluster:
  - **ASGI Master**: Gunicorn with 4 isolated Uvicorn workers (`-k uvicorn.workers.UvicornWorker -w 4`) for high-concurrency WebSocket streams.
  - **Database Service**: PostgreSQL 16 Alpine container with healthchecks and persistent storage.
- **Headless Runner Non-Interactive Rules**:
  - Always set `export GIT_TERMINAL_PROMPT=0` to prevent Git from blocking on non-existent TTY terminals.
  - Always fetch using the ephemeral `GITHUB_TOKEN` (`https://x-access-token:${GITHUB_TOKEN}@github.com/${{ github.repository }}.git`) to bypass password and macOS Keychain GUI prompts.
  - Every Git synchronization step must include a strict 1-minute timeout (`timeout-minutes: 1`) to fail fast rather than hanging indefinitely.

