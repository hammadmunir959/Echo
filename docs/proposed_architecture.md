# Echo — Proposed Architecture & File Structure

## Design Goals

- **Flat, predictable layout** — no duplicate `core` sub-packages, no ghost directories.
- **Single responsibility per file** — services, API routes, and models are strictly separated.
- **Standard FastAPI project conventions** — `app/` as the main package, thin routers, service layer, dependency injection.
- **No runners directory** — the app is started with `uvicorn app.main:app` (the Python standard).

---

## Proposed File Structure

```
echo/
│
├── app/                              # Main application package
│   ├── __init__.py
│   ├── main.py                       # App factory + lifespan (start pipeline worker)
│   ├── config.py                     # Settings via pydantic-settings or simple dataclass
│   ├── dependencies.py               # FastAPI Depends providers (get_db, get_audio_service)
│   │
│   ├── api/                          # Presentation layer — thin HTTP handlers only
│   │   ├── __init__.py
│   │   ├── router.py                 # Aggregates all sub-routers
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── sessions.py           # POST /sessions/start, POST /sessions/stop
│   │       ├── transcripts.py        # GET /transcripts, GET /search
│   │       ├── action_items.py       # GET /action-items, PATCH /action-items/{id}
│   │       └── stream.py             # GET /sessions/{id}/stream  (SSE)
│   │
│   ├── services/                     # Business logic — pure Python, no FastAPI
│   │   ├── __init__.py
│   │   ├── audio_service.py          # PyAudio + WebRTC VAD + chunking (runs in thread)
│   │   ├── transcription_service.py  # Faster-Whisper wrapper (load/unload)
│   │   ├── summarization_service.py  # llama-cpp-python GGUF wrapper (load/unload)
│   │   ├── pipeline.py               # asyncio pipeline worker (coordinates the above two)
│   │   └── event_bus.py              # In-memory SSE event bus (asyncio.Queue per subscriber)
│   │
│   ├── db/                           # Persistence layer
│   │   ├── __init__.py
│   │   ├── database.py               # SQLite connection manager (WAL mode)
│   │   ├── schema.sql                # Canonical schema (meetings, transcripts, action_items)
│   │   └── repositories/
│   │       ├── __init__.py
│   │       ├── meeting_repo.py       # CRUD for meetings table
│   │       ├── transcript_repo.py    # CRUD + FTS search for transcripts
│   │       └── action_item_repo.py   # CRUD for action_items table
│   │
│   └── models/                       # Pydantic schemas (request/response)
│       ├── __init__.py
│       ├── session.py                # SessionStart, SessionStatus response
│       ├── transcript.py             # Transcript, TranscriptPage
│       └── action_item.py            # ActionItem, ActionItemUpdate
│
├── assets/                           # AI model files (git-ignored)
│   └── qwen2-0_5b-instruct-q4_k_m.gguf
│
├── data/                             # Runtime data (git-ignored)
│   ├── echo.db                       # SQLite database file
│   └── recordings/                   # Temporary WAV chunk files
│
├── docs/                             # Project documentation
│   ├── system_design_analysis.md
│   ├── architecture_analysis.md
│   ├── proposed_system_design.md
│   └── proposed_architecture.md      # (this file)
│
├── tests/                            # Test suite
│   ├── __init__.py
│   ├── conftest.py                   # pytest fixtures (test DB, mock audio)
│   ├── test_transcription_service.py
│   ├── test_summarization_service.py
│   ├── test_pipeline.py
│   └── test_api.py
│
├── .env.example                      # Environment variable template
├── .gitignore
├── .dockerignore
├── Dockerfile
├── docker-compose.yml                # Fixed: api service only (no Redis, no workers)
├── requirements.txt
└── README.md
```

---

## Module Dependency Graph (Proposed — Clean)

```
app/main.py
  ├── app/config.py               (settings read once at startup)
  ├── app/api/router.py           (mounts all sub-routers)
  │     ├── api/v1/sessions.py    ──► services/audio_service.py
  │     ├── api/v1/stream.py      ──► services/event_bus.py
  │     ├── api/v1/transcripts.py ──► db/repositories/transcript_repo.py
  │     └── api/v1/action_items.py──► db/repositories/action_item_repo.py
  │
  └── app/services/pipeline.py   (background asyncio task, started in lifespan)
        ├── services/audio_service.py      (thread → asyncio.Queue)
        ├── services/transcription_service.py → run_in_executor
        ├── services/summarization_service.py → run_in_executor
        ├── db/repositories/transcript_repo.py
        ├── db/repositories/action_item_repo.py
        └── services/event_bus.py          (publish to SSE subscribers)
```

> **Key improvement**: The API layer never imports services directly (except via `Depends`). Services never import the API layer. The pipeline is the only orchestrator.

---

## Key File Responsibilities

| File | Responsibility | Lines (est.) |
|------|----------------|-------------|
| `app/main.py` | FastAPI app factory, lifespan hooks, pipeline startup | ~50 |
| `app/config.py` | All settings from env vars (paths, thresholds, model names) | ~35 |
| `app/dependencies.py` | `Depends` providers for DB session, audio service | ~20 |
| `app/api/v1/sessions.py` | Start/stop recording endpoints | ~40 |
| `app/api/v1/stream.py` | SSE stream endpoint | ~30 |
| `app/api/v1/transcripts.py` | GET / search transcripts | ~30 |
| `app/api/v1/action_items.py` | GET / update action items | ~30 |
| `app/services/audio_service.py` | PyAudio + VAD + 30s chunking | ~120 |
| `app/services/transcription_service.py` | Faster-Whisper load/transcribe/unload | ~50 |
| `app/services/summarization_service.py` | llama-cpp-python load/extract/unload | ~70 |
| `app/services/pipeline.py` | async worker: queue → STT → LLM → DB → SSE | ~60 |
| `app/services/event_bus.py` | In-memory pub/sub for SSE | ~40 |
| `app/db/database.py` | SQLite connection manager (context manager) | ~40 |
| `app/db/repositories/*.py` | SQL queries, one file per domain entity | ~40 each |
| `app/models/*.py` | Pydantic request/response schemas | ~20 each |

---

## API Contract (Proposed)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness probe |
| `POST` | `/api/v1/sessions/start` | Start a recording session → `{ meeting_id, status }` |
| `POST` | `/api/v1/sessions/stop` | Stop recording → `{ meeting_id, status }` |
| `GET` | `/api/v1/sessions/{id}/stream` | SSE stream of `transcript` and `action_item` events |
| `GET` | `/api/v1/transcripts?limit=&offset=` | Paginated transcript list |
| `GET` | `/api/v1/transcripts/search?q=` | FTS5 full-text search |
| `GET` | `/api/v1/action-items?meeting_id=&status=` | Filtered action item list |
| `PATCH` | `/api/v1/action-items/{id}` | Update action item status/owner |

---

## How to Run (Proposed)

```bash
# Development
uvicorn app.main:app --reload --port 8080

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8080 --workers 1

# Docker (single container, no compose needed for basic use)
docker build -t echo .
docker run -p 8080:8080 -v ./data:/app/data -v ./assets:/app/assets echo
```

---

## Removed vs. Added

| Removed | Replaced By |
|---------|-------------|
| `core/celery_app.py` | `asyncio` + `ThreadPoolExecutor` in `pipeline.py` |
| `core/distributed_tasks.py` | `app/services/pipeline.py` |
| `core/task_queue.py` | `asyncio.Queue` (in-memory, no DB overhead) |
| `core/orchestrator.py` | `app/services/pipeline.py` |
| `core/` package | `app/services/` package |
| `database/` package | `app/db/` package |
| `runners/` directory | `uvicorn app.main:app` directly |
| `api/core/` sub-package | `app/dependencies.py` |
| Redis PubSub + WebSocket | `app/services/event_bus.py` + SSE |
| Global `CURRENT_MEETING_ID` | Meeting ID stored in SQLite + returned to client |
| Ghost `core/database/`, `core/models/`, `core/recordings/` | Gone |
| Inline `try/except ALTER TABLE` migrations | `schema.sql` as single source of truth |
