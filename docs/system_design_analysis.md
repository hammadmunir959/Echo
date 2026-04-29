# Echo — Current System Design Analysis

## Overview

**Echo** is a local AI-powered meeting assistant. It captures live audio from a microphone, performs Voice Activity Detection (VAD), chunks speech into 30-second WAV files, transcribes them using **Faster-Whisper**, extracts **action items** using a local **Qwen2-0.5B GGUF** model (via llama.cpp), and persists everything to **SQLite**. A FastAPI server exposes REST endpoints for control and data retrieval, and a WebSocket endpoint for real-time browser updates.

---

## Current System Components

### 1. Audio Capture (`core/audio_stream.py`)
- Uses **PyAudio** to read the microphone at 16kHz, 16-bit mono, 30ms frame chunks.
- Uses a **dual-gate VAD**: first RMS energy threshold check, then **WebRTC VAD** (`webrtcvad`).
- Maintains a **pre-roll buffer** (1.5s) and a **post-roll counter** (2.0s) for clean speech boundaries.
- Every **30 seconds** of speech, the buffer is flushed to a `.wav` file in `recordings/`.
- After saving the chunk, it calls `task_transcribe.delay(...)` — a **Celery** async task.

### 2. Task System — DUAL SYSTEM (Critical Design Flaw)
The project simultaneously implements **two separate, competing task systems**:

#### a) Celery + Redis (`core/celery_app.py`, `core/distributed_tasks.py`)
- A full Celery broker/backend setup routing tasks through **Redis**.
- Two tasks: `echo.tasks.transcribe` and `echo.tasks.summarize`.
- Workers are started as separate OS processes via `runners/worker_stt.py` and `runners/worker_llm.py`.
- Requires a **Redis server** running externally.

#### b) SQLite-Backed Custom Task Queue (`core/task_queue.py`, `core/orchestrator.py`)
- A hand-rolled `TaskQueue` class using a `task_queue` SQLite table.
- An `Orchestrator` class running a **polling worker loop** in a `daemon Thread`.
- Implements enqueue, fetch-next, mark-completed, mark-failed, retry, and stall-recovery logic.
- Fully self-contained — no external dependencies.

> ⚠️ **Both systems exist in the codebase simultaneously.** `audio_stream.py` calls Celery (`task_transcribe.delay`), while the `Orchestrator` and `TaskQueue` are unused dead code that polls SQLite. This is the single biggest source of confusion.

### 3. Transcription Service (`core/transcriber.py`)
- Wraps **Faster-Whisper** (CTranslate2-based) in a `Transcriber` class.
- Implements **load-on-use / unload-after-use** strategy to free RAM between calls (sequential model loading).
- Returns `(full_text: str, segments: list[dict])`.

### 4. Summarization / LLM Service (`core/summarizer.py`)
- Wraps **llama-cpp-python** loading a local **Qwen2-0.5B-Instruct GGUF** file.
- Uses a **GBNF grammar** with `LlamaGrammar` to force structured JSON output.
- Same load/unload strategy as the Transcriber.
- Note: `distributed_tasks.py` calls `summarizer.extract_action_items()` but the Summarizer class only has `summarize()`. This is a **broken method call** (runtime `AttributeError`).

### 5. Model Manager (`core/model_manager.py`)
- Provides path resolution for the Whisper and Qwen GGUF models.
- Auto-downloads the Qwen GGUF from HuggingFace Hub on first launch.

### 6. Database (`database/db_manager.py`, `database/schema.sql`)
- **SQLite** with WAL mode and `PRAGMA synchronous=NORMAL` for concurrent reads.
- Schema: `meetings`, `transcripts`, `action_items`, `task_queue` (4 tables).
- Inline schema migration via `ALTER TABLE ... ADD COLUMN` wrapped in `try/except`.
- **FTS5** virtual table (`transcripts_fts`) with INSERT/DELETE/UPDATE triggers for full-text search.

### 7. API Layer (`api/`)
```
api/
├── app.py              # FastAPI factory with lifespan
├── core/
│   └── security.py     # API key auth (X-API-Key header)
└── v1/
    ├── router.py
    └── endpoints/
        ├── control.py  # POST /start, POST /stop
        ├── data.py     # GET /transcripts, /action-items, /search
        └── stream.py   # WS /meetings/{id}
```
- `app.py` calls `create_app()` which registers the V1 router under `/api/v1`.
- **`control.py`** uses a **module-level global** `CURRENT_MEETING_ID` for mutable state — fragile and non-reentrant.
- `stream.py` opens a new **Redis PubSub connection per WebSocket client**.

### 8. Runners (`runners/`)
- `api_server.py` — Starts uvicorn pointing at `api.app:app`.
- `worker_stt.py` — Spawns a Celery STT worker via `subprocess.run`.
- `worker_llm.py` — Spawns a Celery LLM worker via `subprocess.run`.
- `interactive_test.py` — A standalone test/demo script (not part of production).

### 9. Infrastructure (`docker-compose.yml`, `Dockerfile`)
- Defines 4 services: `echo-redis`, `echo-api`, `worker-stt`, `worker-llm`.
- Docker Compose references `python server.py` as the API entry point — but `server.py` **does not exist** at the project root. Entry point is broken.

---

## Data Flow (As Implemented via Celery Path)

```
Microphone
    │
    ▼
AudioStream (PyAudio + WebRTC VAD)
    │  30s speech chunk
    ▼
WAV File saved to recordings/
    │
    ▼
task_transcribe.delay(path, meeting_id)  ─── Celery Task ───►  Redis Broker
                                                                      │
                                                               STT Worker Process
                                                                      │
                                                            faster-whisper transcribe()
                                                                      │
                                                            INSERT into transcripts
                                                                      │
                                              ┌───────────────────────┘
                                              │  task_summarize.delay(text, meeting_id)
                                              ▼
                                       Redis Broker ──► LLM Worker Process
                                                               │
                                                     summarizer.extract_action_items()
                                                     [BROKEN: method does not exist]
                                                               │
                                                     INSERT into action_items
                                                               │
                                              ┌────────────────┘
                                              │  r.publish(f"meeting:{id}", event)
                                              ▼
                                       Redis PubSub Channel
                                              │
                                              ▼
                                     WebSocket Endpoint ──► Browser Client
```

---

## Identified Design Problems

| # | Problem | Location | Severity |
|---|---------|----------|----------|
| 1 | **Dual task system** — Celery+Redis AND SQLite TaskQueue+Orchestrator coexist | `core/task_queue.py`, `core/orchestrator.py`, `core/celery_app.py` | 🔴 Critical |
| 2 | **Broken method call** — `distributed_tasks.py` calls `summarizer.extract_action_items()` which doesn't exist | `core/distributed_tasks.py:71` | 🔴 Critical |
| 3 | **Broken Docker entry point** — `docker-compose.yml` runs `python server.py` but file doesn't exist | `docker-compose.yml:15` | 🔴 Critical |
| 4 | **Global mutable state in API** — `CURRENT_MEETING_ID` module-level variable in control endpoint | `api/v1/endpoints/control.py:20` | 🟠 High |
| 5 | **Celery + Redis overkill** — app runs on a single machine, accessing local microphone and local models | All Celery infrastructure | 🟠 High |
| 6 | **SQLite TaskQueue is dead code** — `Orchestrator.start_worker()` is never called from app lifecycle | `core/orchestrator.py`, `core/task_queue.py` | 🟠 High |
| 7 | **Duplicate nested directories** — `core/database/`, `core/models/`, `core/recordings/` exist inside `core/` alongside top-level equivalents | `core/` subdirectories | 🟡 Medium |
| 8 | **Redis connection per WebSocket** — a new Redis client opened for every connected browser tab | `api/v1/endpoints/stream.py` | 🟡 Medium |
| 9 | **Summarizer method mismatch** — Orchestrator calls `summarizer.summarize()` but distributed_tasks calls `summarizer.extract_action_items()` | Inconsistency across files | 🟡 Medium |
| 10 | **Double `from fastapi import FastAPI`** in `app.py` — redundant import | `api/app.py:1,24` | 🟢 Low |
| 11 | **`runners/` adds sys.path manually** — non-standard, fragile import path management | `runners/*.py` | 🟢 Low |
| 12 | **Inline DB migrations** — schema evolution mixed into `init_db()` with bare try/except | `database/db_manager.py:42-75` | 🟢 Low |
| 13 | **Config class runs on import** — `Config.initialize_directories()` has a side-effect at module level | `core/config.py:47` | 🟢 Low |
