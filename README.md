# Echo HQ — Dispatch Transcription System 

**Echo HQ** is a high-performance, production-grade transcription server designed for organizations operating complex multi-node radio/dispatch networks (Police, Rescue, Edhi, etc.).

It establishes a hierarchical monitoring system where field nodes (walkie-talkies, satellite phones) transmit audio chunks to a central Headquarters. These chunks are transcribed in real-time using a local, thread-safe AI pipeline, tagged with organization-level metadata, and stored for instant search and audit.

## Key Features
- **Hierarchical Governance:** Multi-tenant support with a tiered structure: `Organization` ⮕ `Station` ⮕ `Node`.
- **Parallel AI Pipeline:** Uses an `asyncio.Queue` distributed across a thread-local pool of **Faster-Whisper** workers for maximum CPU utilization.
- **Micro-batch Ingestion:** Handled via REST API with automated validation, storage, and background processing.
- **Real-time SSE Stream:** Operators receive live transcripts and AI analysis via Server-Sent Events (SSE).
- **Post-Processing Intelligence:** Local LLM integration (**llama.cpp**) for automated summarization and entity extraction using **Qwen-2.5** and **GBNF grammars**.
- **Enterprise Search:** Tiered retrieval with full JSON analysis results stored for every transcript.

## Pipeline Architecture

Echo HQ uses a modular, non-blocking architecture that separates audio ingestion, transcription, and post-processing.

```mermaid
graph TD
    subgraph "Ingestion"
        N[Field Node] -->|POST /audio| API[FastAPI Ingest]
        API --> STO[Storage Service]
        STO -->|Enqueue| Q[asyncio.Queue]
    end

    subgraph "Processing Pipeline"
        Q --> W["Worker Thread"]
        W --> WHI["Faster-Whisper (Transcription)"]
        WHI --> LLM["llama.cpp (Post-Processing)"]
        LLM --> GBNF["GBNF Grammar Enforcement"]
        GBNF --> DB[(PostgreSQL)]
    end

    subgraph "Egress"
        DB --> BUS[Event Bus]
        BUS --> SSE[SSE Stream]
        SSE --> DASH[HQ Dashboard]
    end
```

### End-to-End Data Flow

1.  **Ingestion:** Field nodes send audio chunks via the `/ingest` API.
2.  **Transcription:** Background workers use `Faster-Whisper` (with thread-local pools) to convert audio to text.
3.  **Post-Processing:** The `PostProcessingService` invokes a local LLM (**Qwen-2.5**) via `llama.cpp`.
4.  **Structured Analysis:** A **GBNF grammar** enforces a strict JSON schema, extracting incident types, urgency, and specific entities from the transcript.
5.  **Persistence & Broadcast:** The final combined record (raw text + structured JSON) is saved to PostgreSQL and broadcasted via SSE.

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

### Core Settings
| Variable | Description | Default |
|----------|-------------|---------|
| `ECHO_POSTGRES_DSN` | PostgreSQL connection string | (Required) |
| `ECHO_API_KEY` | Security key for all requests | `echo_hq_key` |
| `ECHO_LOG_LEVEL` | Logging verbosity (`INFO`, `DEBUG`) | `INFO` |
| `ECHO_AUDIO_DIR` | Path to store ingested audio | `data/audio` |

### Transcription Settings
| Variable | Description | Default |
|----------|-------------|---------|
| `ECHO_WHISPER_MODEL` | Whisper model size (`base`, `small`, `medium`) | `base` |
| `ECHO_DEVICE` | Hardware device (`cpu`, `cuda`) | `cpu` |
| `ECHO_BEAM_SIZE` | Transcription quality (1-10) | `5` |
| `ECHO_VAD_FILTER` | Voice Activity Detection | `True` |

### LLM Post-Processing (llama.cpp)
| Variable | Description | Default |
|----------|-------------|---------|
| `ECHO_LLM_MODEL_PATH` | Path to Qwen-2.5 GGUF model | (Required) |
| `ECHO_LLM_N_CTX` | LLM Context window size | `4096` |
| `ECHO_LLM_N_GPU_LAYERS` | GPU offloading layers | `0` |
| `ECHO_LLM_TEMPERATURE` | Generation randomness | `0.1` |
