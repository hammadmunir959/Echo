# 🛠️ Technical Specifications: Echo

**Project:** Echo  
**Version:** 1.0  
**Type:** Implementation Spec  
**Based On:** `echo_prd.md`, `echo_system_design.md`

---

## 1. Technology Stack Specs

| Component | Technology | Version / Config | Reasoning |
|-----------|------------|------------------|-----------|
| **Language** | Python | 3.10+ | Robust ecosystem for AI/ML bindings. |
| **SLM Runtime** | `llama-cpp-python` | Latest (CUBLAS enabled if Desktop) | Best-in-class local inference speed & Python bindings. |
| **Model** | Qwen 2.5/3 0.6B Instruct | GGUF (Q4_K_M) | Optimal balance of size (<500MB) and instruction following. |
| **Transcription** | `faster-whisper` | **Base.en** (Default). Configurable (Tiny/Small/Medium/Large). | Base offers best balance of speed/accuracy. |
| **Queue System** | SQLite-based | Persistent Job Queue | Ensures task recovery after crash. |
| **Database** | SQLite3 (WAL Mode) | Enabled | High concurrency for background workers. |
| **VAD Engine** | `silero-vad` | Latest | Lightweight silence detection. |
| **Orchestration** | Native Python | AsyncIO | Lightweight control of I/O bound tasks. |
| **Tools Protocol** | MCP (Internal) | JSON-RPC 2.0 style | Future-proofing for external agent connections. |

---

## 2. Project Directory Structure

```text
echo/
├── main.py                 # Entry point (CLI for now)
├── config.py               # Global settings (paths, model params)
├── core/
│   ├── engine.py           # SLM Inference Wrapper (llama.cpp)
│   ├── grammars.py         # GBNF Grammar Definitions
│   ├── orchestrator.py     # Main Agent Loop
│   ├── audio_stream.py     # Continuous Audio Input Handler
│   ├── task_queue.py       # Persistent Queue Logic
│   └── model_manager.py    # Auto-downloader for Whisper/Qwen
├── database/
│   ├── schema.sql          # CREATE TABLE statements
│   └── db_manager.py       # SQLite interaction layer
├── tools/
│   ├── __init__.py         # Tool registry
│   ├── audio.py            # Whisper transcription logic
│   └── storage.py          # Database read/write tools
├── models/                 # Downloaded GGUF models go here
└── recordings/             # User audio files
```

---

## 3. Database Schema (SQLite)

### 3.1 Database Configuration (WAL Mode)
SQLite will be initialized with **Write-Ahead Logging** to support simultaneous record-and-process workflows.
```python
db.execute("PRAGMA journal_mode=WAL;")
db.execute("PRAGMA synchronous=NORMAL;")
```

### 3.2 Meetings Table
```sql
CREATE TABLE IF NOT EXISTS meetings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    duration_seconds INTEGER,
    audio_path TEXT NOT NULL,
    status TEXT CHECK(status IN ('pending', 'processing', 'completed', 'failed')) DEFAULT 'pending'
);
```

### 3.2 Transcripts Table
```sql
CREATE TABLE IF NOT EXISTS transcripts (
    meeting_id INTEGER PRIMARY KEY,
    raw_text TEXT,
    segments_json TEXT, -- JSON array of {start, end, text}
    FOREIGN KEY(meeting_id) REFERENCES meetings(id)
);
```

### 3.3 Action Items Table
```sql
CREATE TABLE IF NOT EXISTS action_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    meeting_id INTEGER,
    description TEXT NOT NULL,
    owner TEXT,
    due_date TEXT,
    status TEXT DEFAULT 'open',
    FOREIGN KEY(meeting_id) REFERENCES meetings(id)
);
```

---

### 3.4 **Task Queue Table** (For Persistence)
```sql
CREATE TABLE IF NOT EXISTS task_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_type TEXT NOT NULL, -- 'transcribe', 'summarize'
    payload TEXT NOT NULL,   -- JSON (e.g., audio chunk path)
    status TEXT DEFAULT 'pending', -- 'pending', 'processing', 'failed', 'completed'
    retry_count INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    error_log TEXT
);
```

---

## 4. MCP Tool Definitions & Schemas

The Agent will see these function signatures in its system prompt.

### 4.1 Tool: `save_plan`
**Description:** Persist the extracted action items and summary.
**JSON Schema:**
```json
{
  "type": "function",
  "function": {
    "name": "save_plan",
    "description": "Save the meeting summary and action items.",
    "parameters": {
      "type": "object",
      "properties": {
        "summary": { "type": "string" },
        "action_items": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "description": { "type": "string" },
              "owner": { "type": "string" },
              "due_date": { "type": "string", "description": "ISO 8601 format YYYY-MM-DD" }
            },
            "required": ["description"]
          }
        }
      },
      "required": ["summary", "action_items"]
    }
  }
}
```

---

## 5. GBNF Grammar Implementation

To ensure the SLM *only* outputs valid JSON for the `save_plan` tool, we will use a GBNF grammar.

**Logic:**
1.  Define a grammar that forces the output to start with `{ "tool_use": ... }` or directly the JSON arguments.
2.  Pass this grammar to `llama_cpp.Llama.__call__(..., grammar=...)`.

**Rough GBNF Spec:**
```gbnf
root ::= "{" space "\"summary\"" space ":" space string "," space "\"action_items\"" space ":" space items_list "}"
items_list ::= "[" space (item ("," space item)*)? "]"
item ::= "{" space "\"description\"" space ":" space string ... "}"
string ::= "\"" ([^"\\] | "\\" .)* "\""
space ::= [ \t\n]*
```
*(Note: We will use the `llama_cpp.LlamaGrammar.from_json_schema` helper in the actual code to generate this automatically from the Pydantic model explained above.)*

---

## 6. Algorithms & Logic Flow

### 6.1 The "Continuous Listening" Pipeline (VAD-Gated)
1.  **Audio Stream:** `audio_stream.py` listens to mic.
2.  **VAD Gate:** Apply `silero-vad`. If silent > 5s, drop buffer.
3.  **Chunking:** Save voice-active audio in 30s chunks to disk.
4.  **Enqueue:** Add to `task_queue`.

### 6.2 The "Rolling Summary" Worker
To handle long meetings without context overflow:
1.  **Fetch Chunk:** Worker picks up transcription task.
2.  **Transcribe:** Whisper Base processes the chunk.
3.  **Summarize:** 
    *   Prompt: `[Existing Summary Context] + [New Transcript Segment]`.
    *   SLM generates updated summary and new action items.
4.  **Sequential Memory:** Whisper and Qwen are loaded/unloaded sequentially to stay under the 1GB RAM budget.

### 6.2 The "End Meeting" / Finalization
1.  **Stop:** User stops recording. Queue continues processing.
2.  **Drain:** Worker finishes all chunks in queue.
3.  **Finalize:** Once queue empty, generate final "Meeting Report" using aggregated text.

---

## 7. Edge Cases & Error Handling

*   **Transcription Fail:** If Whisper returns < 10 words, mark meeting as "Empty" and skip Agent.
*   **Model Timeout:** If inference takes > 60s, kill process and save "Partial Summary".
*   **Audio Corruption:** Check `os.path.getsize > 0` before processing.

---

## 8. Deployment Strategy (Local)

*   **Environment:** `venv` managed by Poetry or `requirements.txt`.
*   **Assets:**
    *   `qwen2.5-0.5b-instruct-q4_k_m.gguf` (~400MB) - Auto-download functionality on first run.
    *   Whisper models cached in `~/.cache/huggingface`.

