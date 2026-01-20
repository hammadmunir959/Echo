# 📟 Echo: Secure On-Device Agentic AI System Design

**Project Name:** Echo  
**Version:** 2.0 (The Potato Stack)  
**Domain:** Agentic AI + SLMs  
**Goal:** A privacy-first, on-device agent for meeting minutes and action item automation.

---

## 1️⃣ High-Level Architecture (The Potato Stack)

Echo uses a **Store-and-Forward** Modular Monolith architecture optimized for **resilience** and **legacy hardware compatibility** (Zero-AVX).

```mermaid
graph TD
    User((User Voice)) -->|Mic Input| AudioEngine[Audio Engine]
    
    subgraph "Phase 1: Real-Time Listener (C-based)"
        AudioEngine -->|16kHz Stream| VAD{WebRTC VAD}
        VAD -->|Active Speech| Buffer[Rolling Buffer]
        VAD -->|Silence| Discard[Drop Frame]
        Buffer -->|30s Chunk| WAVFile[Save .wav]
    end

    WAVFile -->|Enqueue Task| DB[(SQLite Queue)]

    subgraph "Phase 2: Asynchronous Processor (Python)"
        DB -->|Fetch Task| Orchestrator[Orchestrator]
        
        subgraph "Resilience Layer"
            Orchestrator -->|Startup| Recovery[Zombie Task Scavenger]
            Orchestrator -->|Runtime| Retry[Retry Logic (Max 5)]
        end

        Orchestrator -->|Task: Transcribe| Whisper[Faster-Whisper INT8]
        Whisper -->|Raw Text| TranscriptTable[DB: Transcripts]
        
        TranscriptTable -->|New Text| Qwen[Qwen2-0.5B GGUF]
        Qwen -->|Reasoning + GBNF| JSON[Structured JSON]
        JSON -->|Action Items| ActionTable[DB: Action Items]
    end
```

---

## 2️⃣ Resilience & Error-Proofing Strategy

### 🛡️ 1. The "Store-and-Forward" Guarantee
**Risk**: App crashes mid-meeting (e.g., OOM, Battery die).
**Solution**:
1.  Audio is flushed to disk every 30 seconds.
2.  The `queue_task` is written to SQLite *after* file flush.
3.  **Result**: Maximum data loss is limited to the last <30s buffer. All previous audio is safe on disk and queued for processing next run.

### 🧟 2. Zombie Task Recovery
**Risk**: System crashes while a task is in `processing` state. On restart, the task remains `processing` forever.
**Solution**:
- **Mechanism**: On startup, `TaskQueue.recover_stalled_tasks()` executes.
- **Logic**: `UPDATE task_queue SET status = 'pending' WHERE status = 'processing'`.
- **Result**: Self-healing. Interrupted tasks are automatically re-queued.

### 🛑 3. Dead Letter Handling
**Risk**: A malformed audio file crashes the inference engine repeatedly.
**Solution**:
- **Retry Count**: Each task has a `retry_count`.
- **Logic**: If `retry_count >= 5`, task is marked `failed` and logged. It is NOT picked up again, preventing infinite crash loops.

### ⚡ 4. Concurrency Safety
**Risk**: UI reads data while Background Worker writes it.
**Solution**:
- **WAL Mode (Write-Ahead Logging)**: Enabled in SQLite. Allows simultaneous Readers and Writers.
- **Transactions**: State transitions (`pending` -> `processing`) happen inside atomic DB transactions.

---

## 3️⃣ Performance Strategy (Potato Requirements)

### 🔋 Compute Optimization
- **VAD Gating**: The *Whisper* engine is expensive. We run `webrtcvad` (C-based, negligible CPU) on the audio stream first. If silence > 500ms, we drop the frame.
- **Model Unloading**: We cannot keep Whisper and Qwen loaded simultaneously on 8GB devices.
    - *Pipeline:* Load Whisper -> Transcribe -> Unload.
    - *Pipeline:* Load Qwen -> Summarize -> Unload.

### 🧠 Rolling Context Window
- **Risk**: Qwen 0.5B has limited context (8k/32k). Long meetings will overflow.
- **Solution**:
    - Maintain a "Running Summary" (~500 tokens).
    - For each new chunk: Input = `[Running Summary] + [New Transcript Chunk]`.

---

## 4️⃣ Security Design

- **Encryption at Rest**: Optional SQLCipher for the local database.
- **Zero-Trust Networking**: The app does not request `INTERNET` permission (on Android) to prove privacy.
- **Input Validation**: API layer uses Pydantic to strictly validate all incoming control requests.

---

## 5️⃣ Tradeoffs

- **Latency vs. Reliability**: We chose *Reliability*. Audio is processed in batches (30s latency), not real-time. This ensures no data is lost if the CPU spikes.
- **Model Size vs. Intelligence**: We chose *Compatibility*. `Qwen-0.5B` runs on anything but requires strict GBNF prompting to be useful.
