# Echo HQ — Dispatch Transcription System 

**Echo HQ** is a high-performance, production-grade transcription server designed for organizations operating complex multi-node radio/dispatch networks (Police, Rescue, Edhi, etc.).

It establishes a hierarchical monitoring system where field nodes (walkie-talkies, satellite phones) transmit audio chunks to a central Headquarters. These chunks are transcribed in real-time using a local, thread-safe AI pipeline, tagged with organization-level metadata, and stored for instant search and audit.

## Key Features
- **Hierarchical Governance:** Multi-tenant support with a tiered structure: `Organization` ⮕ `Station` ⮕ `Node`.
- **Parallel AI Pipeline:** Uses an `asyncio.Queue` distributed across a thread-local pool of **Faster-Whisper** workers for maximum CPU utilization.
- **Micro-batch Ingestion:** Handled via REST API with automated validation, storage, and background processing.
- **Real-time SSE Stream:** Operators receive live transcripts via Server-Sent Events (SSE) with millisecond latency.
- **Enterprise Search:** Fuzzy search (ILIKE) and tiered retrieval by Organization, Station, or Node.
- **Robust Infrastructure:** PostgreSQL persistence, structured logging (`structlog`), and FastAPI lifespan management for AI model readiness.

## Pipeline Architecture

Echo HQ uses a non-blocking, producer-consumer architecture to handle high-concurrency audio ingestion and processing.

```mermaid
graph TD
    subgraph "Ingestion (Producer)"
        N[Field Node] -->|POST /audio| API[FastAPI Ingest]
        API --> VAL[Audio Validator]
        VAL --> STO[Storage Service]
        STO -->|Enqueue Job| Q[asyncio.Queue]
    end

    subgraph "Transcription (Consumer Pool)"
        Q --> W1["Worker 1 (Thread)"]
        Q --> W2["Worker 2 (Thread)"]
        QN["Worker N (Thread)"]
        
        W1 & W2 & QN --> BUS[Internal Event Bus]
        W1 & W2 & QN --> DB[(PostgreSQL)]
    end

    subgraph "Egress (Real-time)"
        BUS --> SSE[SSE /api/v1/stream]
        SSE --> DASH[HQ Dashboards]
    end
```

### End-to-End Data Flow

1.  **Ingestion:** Field nodes send audio chunks (60s max) via multipart FORM data. 
2.  **Validation & Storage:** The `AudioValidator` checks MIME types and bitrates. Validated audio is persisted to disk by the `StorageService`, generating a unique file path.
3.  **Queuing:** A `TranscriptionJob` metadata object is pushed into a global `asyncio.Queue`.
4.  **Async Orchestration:** The `pipeline_worker` pops jobs from the queue. Since transcription is CPU-intensive, it offloads the work to a thread pool using `loop.run_in_executor`.
5.  **AI Transcription:** The `TranscriptionService` invokes **Faster-Whisper**. 
    > [!NOTE]
    > **Concurrency Management:** To avoid GIL contention and model loading overhead, each worker thread maintains its own **thread-local instance** of the Whisper model.
6.  **Persistence:** The worker ensures the Organization/Station/Node hierarchy exists in PostgreSQL (Upsert) before saving the transcript with word-level timestamps.
7.  **Broadcast:** The finished transcript is published to the `event_bus`, which triggers an SSE broadcast to all connected operators.

### Transcription Service (Under the Hood)
The core AI logic is powered by `faster-whisper`, a re-implementation of OpenAI's Whisper using CTranslate2.
- **Model Quantization:** Uses `int8` quantization for efficient CPU inference.
- **Beam Search:** Configured with `beam_size=5` for a balance between speed and accuracy.
- **Word-Level Timing:** Enabled to allow operators to jump to specific points in the audio during review.

## API Quick Start

### 1. Ingest Audio
Nodes transmit chunks (typically 30-60s) with hierarchical metadata:
```bash
curl -X POST http://hq-server:8080/api/v1/ingest/audio \
  -H "X-API-Key: your_echo_key" \
  -F "audio=@chunk.wav" \
  -F "node_id=UNIT-7" \
  -F "station_id=SOUTH-STATION"
```

### 2. Search & Retrieval
Filter by organization, station, or perform fuzzy searches:
```bash
# Search transcripts by content
curl "http://hq-server:8080/api/v1/transcripts/search?q=emergency" \
  -H "X-API-Key: your_echo_key"

# List transcripts for a specific station
curl "http://hq-server:8080/api/v1/transcripts/station/SOUTH-STATION" \
  -H "X-API-Key: your_echo_key"
```

### 3. Real-time Monitoring
Connect to the stream for instant dispatch updates:
```bash
curl -N http://hq-server:8080/api/v1/stream \
  -H "X-API-Key: your_echo_key"
```

## Setup & Deployment

### Local Development
1. Install dependencies: `pip install -r requirements.txt`
2. Configure `.env` (refer to `.env.example`):
   ```bash
   ECHO_API_KEY=your_key
   ECHO_POSTGRES_DSN=postgresql://user:pass@localhost/echo_db
   ```
3. Run the server: `uvicorn app.main:app --reload --port 8080`

### Docker Deployment
```bash
docker-compose up -d
```

## Configuration (Environment Variables)
All settings use the `ECHO_` prefix:
| Variable | Description | Default |
|----------|-------------|---------|
| `ECHO_POSTGRES_DSN` | PostgreSQL connection string | (Required) |
| `ECHO_WHISPER_MODEL` | AI model size (`tiny`, `base`, `small`, `medium`) | `base` |
| `ECHO_TRANSCRIPTION_WORKERS` | Parallel Whisper threads | `4` |
| `ECHO_API_KEY` | Security key for all requests | `echo_hq_key` |
| `ECHO_LOG_LEVEL` | Logging verbosity (`INFO`, `DEBUG`) | `INFO` |
| `ECHO_AUDIO_DIR` | Path to store ingested audio | `data/audio` |
