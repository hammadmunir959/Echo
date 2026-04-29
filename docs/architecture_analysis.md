# Echo — Current Architecture Analysis

## Project File Structure (Actual)

```
echo/
├── api/                          # FastAPI application
│   ├── app.py                    # ✅ App factory (lifespan, mounts router)
│   ├── core/                     # ⚠️  Misnamed — "core" inside "api"
│   │   └── security.py           # API key auth
│   └── v1/
│       ├── router.py             # Aggregates routers
│       └── endpoints/
│           ├── control.py        # POST /start, /stop
│           ├── data.py           # GET transcripts, action-items, search
│           └── stream.py         # WS /meetings/{id} (Redis PubSub)
│
├── core/                         # Business logic "core"
│   ├── __init__.py
│   ├── config.py                 # Config class (paths, constants)
│   ├── audio_stream.py           # Microphone capture + WebRTC VAD
│   ├── transcriber.py            # Faster-Whisper wrapper
│   ├── summarizer.py             # llama-cpp-python Qwen GGUF wrapper
│   ├── model_manager.py          # Model path resolution + HF download
│   ├── celery_app.py             # ⚠️  Celery app setup
│   ├── distributed_tasks.py      # 🔴 Celery tasks (has broken method call)
│   ├── task_queue.py             # 🔴 SQLite TaskQueue (DEAD CODE)
│   ├── orchestrator.py           # 🔴 Thread worker (DEAD CODE)
│   ├── database/                 # 🔴 Duplicate ghost directory
│   ├── models/                   # 🔴 Duplicate ghost directory
│   └── recordings/               # 🔴 Duplicate ghost directory
│
├── database/                     # SQLite database
│   ├── __init__.py
│   ├── db_manager.py             # DatabaseManager class
│   ├── schema.sql                # Table definitions
│   └── echo.db                   # SQLite file (runtime artifact)
│
├── models/                       # Downloaded AI models
│   └── qwen2-0_5b-instruct-q4_k_m.gguf  # 380MB GGUF model
│
├── recordings/                   # Runtime WAV chunks (transient)
│
├── runners/                      # Process launchers
│   ├── api_server.py             # ⚠️  Wraps uvicorn in argparse
│   ├── worker_stt.py             # ⚠️  Spawns celery via subprocess
│   ├── worker_llm.py             # ⚠️  Spawns celery via subprocess
│   └── interactive_test.py       # Dev/debug script
│
├── logs/                         # Log files (runtime)
├── bin/                          # Empty (placeholder?)
├── scripts/                      # Empty (placeholder?)
│
├── Dockerfile
├── docker-compose.yml            # 🔴 Broken (server.py doesn't exist)
├── requirements.txt
└── README.md
```

---

## Architecture Layers (Current)

```
┌──────────────────────────────────────────────────┐
│                   Presentation Layer              │
│         FastAPI (api/)  ·  Pydantic Models        │
│   /control   /data   /stream (WebSocket + Redis)  │
└────────────────────────┬─────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────┐
│                  Business Logic Layer             │
│              core/ (partially correct)            │
│  AudioStream · Transcriber · Summarizer           │
│  ModelManager · Config                            │
│                                                   │
│  + DEAD CODE: TaskQueue · Orchestrator            │
│  + BROKEN:    CeleryApp · DistributedTasks        │
└──────────────┬─────────────────┬─────────────────┘
               │                 │
┌──────────────▼──┐   ┌──────────▼──────────────────┐
│  Persistence    │   │      External Services        │
│  SQLite (WAL)   │   │  Redis (Broker+Backend)       │
│  schema.sql     │   │  [Required for Celery only]   │
└─────────────────┘   └─────────────────────────────┘
```

---

## Module Dependency Graph (Current — Problematic)

```
api/app.py
  ├── database.db_manager  (direct import = tight coupling)
  ├── core.audio_stream    (direct import — hard to test)
  └── api.v1.router
        ├── endpoints.control
        │     ├── database.db_manager
        │     └── core.audio_stream       (global CURRENT_MEETING_ID)
        ├── endpoints.data
        │     └── database.db_manager
        └── endpoints.stream
              └── redis.asyncio           (new connection per request)

core/audio_stream.py
  ├── core.config
  └── core.distributed_tasks              (tight Celery coupling)
        ├── core.celery_app
        ├── core.transcriber
        ├── core.summarizer               (BROKEN: wrong method name)
        └── database.db_manager

core/orchestrator.py  [DEAD, never started]
  ├── database.db_manager
  ├── core.task_queue                     [DEAD]
  ├── core.transcriber
  └── core.summarizer
```

---

## Infrastructure Complexity Score

| Component | Justification for Use | Is it Justified? |
|-----------|----------------------|-----------------|
| FastAPI | REST API + WebSocket | ✅ Yes |
| SQLite | Persistent local data storage | ✅ Yes |
| PyAudio | Microphone access | ✅ Yes |
| WebRTC VAD | Speech segment detection | ✅ Yes |
| Faster-Whisper | On-device STT | ✅ Yes |
| llama-cpp-python + GGUF | On-device LLM inference | ✅ Yes |
| **Redis** | Used as Celery broker + backend + PubSub | ⚠️ Partially — only PubSub is genuinely useful |
| **Celery** | Distributed task queue | ❌ No — single machine, single process app |
| **SQLite TaskQueue** | Custom task queue backed by DB | ❌ No — duplicates Celery; dead code |
| **Orchestrator** | Thread-based worker | ❌ No — dead code |
| **runners/** | Separate process launcher scripts | ❌ No — just use uvicorn directly |

---

## Key Architectural Anti-Patterns Found

### 1. Dual Task System
The project has evolved two competing systems for async task processing. Neither fully works because `audio_stream.py` routes through Celery, but the SQLite `Orchestrator` was never wired into the app startup. The Celery path has a broken method call that would cause a runtime crash on any actual summarization.

### 2. Infrastructure Mismatch for Project Scale
Echo is explicitly a **local, single-machine tool** (microphone access requires the API to be co-located with the audio hardware). Celery + Redis is designed for **multi-machine horizontal scaling**. This combination is an architectural mismatch — it adds Redis as a required external dependency, makes local dev require docker-compose, and adds 2 extra processes, while providing zero benefit over a simple `asyncio` task or `ThreadPoolExecutor`.

### 3. Broken Encapsulation
The API layer directly accesses `audio_stream` (a hardware resource) via a global singleton and controls it from within an HTTP request handler using a spawned `threading.Thread`. This bypasses the FastAPI lifespan, makes graceful shutdown fragile, and creates a race condition on `CURRENT_MEETING_ID`.

### 4. The `core/` Namespace Collision
There is both a top-level `core/` package and an `api/core/` sub-package. Having two packages named `core` at different levels causes import confusion and is a strong indicator that the project structure was not planned holistically.

### 5. Real-time via Redis vs Simpler Alternatives
WebSocket real-time updates are mediated through Redis PubSub, with a new Redis connection opened per WebSocket client. Since this is a single-process app, a simple `asyncio.Queue` or `SSE` from a shared in-memory event bus would be far simpler, eliminate the Redis dependency, and be more reliable.
