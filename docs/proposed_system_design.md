# Echo — Proposed System Design

## Goal

Simplify Echo to the **minimum viable architecture** that correctly implements its core feature set: **live audio capture → VAD → chunked transcription → LLM action item extraction → persisted results → real-time API**. All infrastructure must be justified by a real requirement.

---

## Design Principles

1. **Single System, No Duplicates** — one task execution pattern, period.
2. **No External Runtime Dependencies** — Redis, Celery, and docker-compose are dropped. The app runs with `python -m uvicorn` and nothing else.
3. **`asyncio`-native** — use FastAPI's async lifespan and `asyncio.Queue` for internal event passing. Background CPU work is offloaded to a `ThreadPoolExecutor` to avoid blocking the event loop.
4. **Separation of Concerns** — API layer does not touch hardware. Services are injected via FastAPI's `Depends`.
5. **One Source of Truth for State** — meeting state lives in SQLite, not in module-level globals.

---

## Core Components (Proposed)

### 1. Audio Service
- **Unchanged logic**: PyAudio + WebRTC VAD + pre/post-roll buffering.
- **Change**: Runs in a **dedicated background thread** (since PyAudio is synchronous).
- On each 30-second chunk, instead of calling `task_transcribe.delay(...)`, it **puts** the file path + meeting ID into a shared `asyncio.Queue`.

### 2. Processing Pipeline (replaces Celery + Orchestrator + TaskQueue)
- A single **`pipeline_worker` async coroutine** is started in the FastAPI lifespan.
- It **gets** items from the `asyncio.Queue`.
- It runs the CPU-bound Whisper and llama.cpp calls in a `ThreadPoolExecutor` using `await loop.run_in_executor(...)`.
- This eliminates Redis, Celery, two worker processes, and all custom task queue/orchestrator code.

```
AudioThread ──► asyncio.Queue ──► pipeline_worker (async coroutine)
                                        │
                          ┌─────────────┼─────────────┐
                          │             │             │
                    run_in_executor  run_in_executor  │
                    (Whisper STT)   (Qwen LLM)        │
                          │             │             │
                    INSERT transcript  INSERT action_items
                          │
                    in-memory EventBus.publish(meeting_id, event)
                          │
                    SSE subscribers get real-time updates
```

### 3. Real-Time Streaming (replaces Redis PubSub + WebSocket)
- Replace the WebSocket + Redis PubSub approach with **Server-Sent Events (SSE)**.
- An in-memory `EventBus` singleton holds a `dict[int, list[asyncio.Queue]]` — one queue per active SSE subscriber.
- `pipeline_worker` calls `event_bus.publish(meeting_id, event)` after each processing step.
- The SSE endpoint is a simple `StreamingResponse` that reads from its queue.
- **No Redis required**. SSE is simpler than WebSocket for server-push-only streams.

### 4. API Layer
- `POST /sessions/start` → creates a meeting in DB, starts AudioService.
- `POST /sessions/stop` → stops AudioService.
- `GET /sessions/{id}/stream` → SSE stream of transcript + action-item events.
- `GET /transcripts` → paginated transcript list.
- `GET /action-items` → paginated action items.
- `GET /search` → FTS5 full-text search.
- `GET /health` → liveness probe.

### 5. Database (unchanged, simplified)
- **SQLite** with WAL mode (unchanged — this is correct).
- Schema: `meetings`, `transcripts`, `action_items`. **Remove `task_queue` table** entirely.
- Migrations moved to explicit versioned scripts, not inline `try/except ALTER TABLE`.

---

## System Architecture Diagram

```
┌────────────────────── FastAPI Process (single) ──────────────────────────┐
│                                                                           │
│   HTTP/SSE Clients                                                        │
│        │                                                                  │
│   ┌────▼──────────────────────────────────────────────────────────────┐  │
│   │                     API Layer (FastAPI)                           │  │
│   │  POST /sessions/start  POST /sessions/stop  GET /sessions/stream  │  │
│   │  GET /transcripts      GET /action-items    GET /search           │  │
│   └──────┬──────────────────────────────────┬───────────────────────┘  │
│          │ start/stop                       │ SSE subscribe             │
│   ┌──────▼───────────┐              ┌───────▼───────────┐              │
│   │  AudioService    │              │    EventBus        │              │
│   │  (Thread)        │              │  (asyncio.Queue)   │◄──────┐     │
│   │  PyAudio+VAD     │              └───────────────────┘       │     │
│   └──────┬───────────┘                                          │     │
│          │ asyncio.Queue.put(chunk)                             │     │
│   ┌──────▼────────────────────────────────────────────────────┐ │     │
│   │              Pipeline Worker (async coroutine)             │ │     │
│   │                                                            │ │     │
│   │  ThreadPoolExecutor                ThreadPoolExecutor      │ │     │
│   │  ┌─────────────────┐              ┌───────────────────┐   │ │     │
│   │  │  Transcriber    │─────────────►│   Summarizer      │   │ │     │
│   │  │  (Faster-Whisper│              │   (llama-cpp-      │   │ │     │
│   │  │   CTranslate2)  │              │    python GGUF)    │   │ │     │
│   │  └─────────────────┘              └──────┬────────────┘   │ │     │
│   │                                          │                 │ │     │
│   │              ┌───────────────────────────┘                 │ │     │
│   │              │  INSERT transcripts + action_items          │ │     │
│   │              ▼                                             │ │     │
│   │         SQLite (WAL)  ──────────────────────────────────► │─┘     │
│   └────────────────────────────────────────────────────────────┘       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## What Is Removed vs. Kept

| Component | Current | Proposed | Reason |
|-----------|---------|----------|--------|
| FastAPI | ✅ Keep | ✅ Keep | Core API framework |
| PyAudio + WebRTC VAD | ✅ Keep | ✅ Keep | Core feature |
| Faster-Whisper | ✅ Keep | ✅ Keep | Core feature |
| llama-cpp-python GGUF | ✅ Keep | ✅ Keep | Core feature |
| SQLite (WAL) | ✅ Keep | ✅ Keep | Correct choice for local app |
| FTS5 search | ✅ Keep | ✅ Keep | Useful feature |
| API Key Auth | ✅ Keep | ✅ Keep | Simple security |
| Docker support | ✅ Keep | ✅ Keep (fixed) | Fix entry point |
| **Redis** | ❌ Drop | | No external dependency need |
| **Celery** | ❌ Drop | | Replaced by asyncio + ThreadPoolExecutor |
| **TaskQueue (SQLite)** | ❌ Drop | | Dead code — asyncio.Queue replaces it |
| **Orchestrator** | ❌ Drop | | Dead code — pipeline_worker replaces it |
| **runners/** scripts | ❌ Drop | | Just use `uvicorn app.main:app` |
| **WebSocket + Redis PubSub** | ❌ Drop | SSE + EventBus | Simpler, no Redis needed |

---

## Dependency Stack (Proposed)

```txt
# Core AI
faster-whisper
llama-cpp-python

# Audio
pyaudio
webrtcvad-wheels

# API
fastapi
uvicorn[standard]
python-multipart

# Data / Utils
pydantic
python-dotenv
scipy
numpy
```

> **Removed**: `redis`, `celery`, `websockets`
> **Added**: `uvicorn[standard]` (includes httptools for SSE performance)
