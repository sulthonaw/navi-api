# Navi API Backend

> **Kiosk-Based Python Examination Platform with Anti-Cheat & Socratic AI Tutoring.**

Navi (*Navigate Your Own Code*) provides a secure backend for university and school coding exams. It locks student kiosks to prevent cheating (instant Alt+Tab detection) while offering intelligent, guarded Socratic hints powered by **Google Gemini** to foster independent problem-solving.

---

## Key Features

- **FastAPI Clean Architecture**: High-speed, async REST API and WebSockets.
- **PostgreSQL 16 & SQLAlchemy 2.0**: Robust relational storage for exam rooms, test cases, student sessions, and audit logs.
- **Socratic AI Hint Engine (Gemini)**: Powered by official `google-genai` SDK with strict guardrails preventing code leakage. Includes offline heuristic fallback.
- **Python AST Validator**: Instant syntax and indentation error checking with line and column accuracy.
- **Sandboxed Execution**: Isolated subprocess runner with strict execution timeouts (default 5.0s) protecting against infinite loops.
- **Real-Time WebSockets**: Live monitoring stream for the teacher dashboard with instant Alt+Tab violation alarms and audible cues.
- **Interactive Swagger & ReDoc**: Full OpenAPI 3.1 documentation with realistic request/response payload examples.
- **Docker Compose Ready**: One-command setup with PostgreSQL and health checks.

---

## Quickstart with Docker Compose

### 1. Clone & Configure Environment
```bash
cp .env.example .env
```
*(Optional)* Add your `GEMINI_API_KEY` in `.env` if you wish to use live Gemini AI. If left empty, the engine uses the built-in deterministic heuristic fallback.

### 2. Launch Services
```bash
docker compose up --build
```
This boots:
- **`navi-postgres`** on port `5432`
- **`navi-api`** on port `8000`

### 3. Access Interactive Documentation
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc UI**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)
- **Raw OpenAPI Spec**: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

---

## Local Development (Without Docker)

### 1. Install Dependencies
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Run the Development Server
```bash
uvicorn app.main:app --reload --port 8000
```

### 3. Run Automated Tests & Linter
```bash
# Run test suite
pytest -v

# Run linter & formatter checks
ruff check .
ruff format --check .
```

### 4. Export Static OpenAPI Documentation
To generate static `openapi.json` and `openapi.yaml` for frontend client generation:
```bash
python scripts/export_openapi.py
```

---

## API Summary

- `GET /health` - System and database health status
- `POST /api/v1/rooms` - Teacher creates exam session (returns 8-character `room_code`)
- `GET /api/v1/rooms/{room_code}` - Get live room status and student roster
- `PATCH /api/v1/rooms/{room_code}/close` - Close exam session
- `POST /api/v1/students/join` - Student kiosk joins exam room
- `GET /api/v1/students/{student_id}` - Query student status and remaining hint quota
- `POST /api/v1/code/run` - Validate syntax and execute code against public test cases
- `POST /api/v1/code/submit` - Final grading against full test suite (including hidden)
- `POST /api/v1/hints/request` - Request Socratic hint for an encountered error
- `POST /api/v1/violations` - Report Alt+Tab / focus loss event
- `WS /api/v1/ws/teacher/{room_code}` - Real-time live dashboard stream
- `WS /api/v1/ws/student/{room_code}/{student_id}` - Student synchronization stream

---

## Documentation for AI Agents

For guidelines on modifying, testing, and maintaining this codebase, refer to [AGENTS.md](file:///e:/navi-api/AGENTS.md).
