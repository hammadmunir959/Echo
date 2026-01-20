# 📋 Product Requirements Document (PRD): Echo

**Project Name:** Echo  
**Version:** 1.0  
**Status:** Draft  
**Last Updated:** 2026-01-20  

---

## 1. Executive Summary
**Echo** is a privacy-first, offline-capable AI agent designed for continuous, resilient, and secure meeting assistance. Unlike cloud-based competitors, Echo processes 100% of data locally and features a robust "store-and-forward" architecture: it continuously listens, queues tasks (transcription, summarization), and processes them in the background. If a step fails, it is retried later, ensuring no data is lost even if the system is overloaded. It leverages SLMs like Qwen 0.6B and configurable Whisper models (Default: Base).

## 2. Problem Statement
*   **Privacy Risk:** Professionals cannot use cloud AI tools for sensitive meetings (NDAs, HIPAA, Classified) due to data leakage risks.
*   **Latency & Connectivity:** Cloud tools fail in low-bandwidth environments (airplanes, remote sites) and suffer from upload lag.
*   **Unstructured Data:** Simple voice recorders leave users with hours of audio to scrub through manually.

## 3. Target Audience
*   **Executives & Legal Counsel:** Individuals who discuss highly sensitive information requiring absolute confidentiality.
*   **Field Researchers/Journalists:** Professionals working in offline/low-connectivity environments.
*   **Privacy Advocates:** Users who philosophically reject cloud-based data mining.

## 4. User Personas
*   **"Secure Sarah" (CISO):** Needs to record board meetings but strictly forbids any device that uploads voice data to AWS/GCP.
*   **"Offline Omar" (Field Geologist):** Dictates notes in remote locations and needs them transcribed and summarized before returning to base.

## 5. Functional Requirements

### 5.1 Core Workflow
| ID | Feature | Description | Priority |
|----|---------|-------------|----------|
| F-001 | **Continuous Listening** | System runs in background, recording and processing audio in chunks (e.g., 30s) continuously. | P0 |
| F-002 | **VAD Gating** | Use Voice Activity Detection to skip processing silence, saving CPU and Battery. | P0 |
| F-003 | **Resilient Processing Queue** | Audio chunks and tasks are added to a persistent queue. Failures are retried automatically. | P0 |
| F-004 | **Local Transcription** | Transcribe using **Whisper Base** (Default). User can switch variants. | P0 |
| F-005 | **Rolling Summarization** | Use a "Running Summary" to handle meetings of any length within SLM context limits. | P0 |
| F-003 | **Intelligent Summarization** | Generate "Meeting Minutes" using Qwen-3-0.6B. Must identify: **Topic**, **Key Decisions**, **Action Items**. | P0 |
| F-004 | **GBNF Enforcement** | The Agent MUST output strictly valid JSON for tool calls (e.g., saving tasks). No free-text hallucinations. | P0 |
| F-005 | **Action Item Database** | Extracted tasks are automatically saved to a local SQLite database (Task, Owner, Due Date). | P1 |
| F-006 | **Search & Retrieve** | Full-text search across past transcripts and summaries. | P2 |

### 5.2 Agent Capabilities (The "Brain")
*   **Model:** Qwen 3-0.6B (Instruct) or equivalent SLM (<1GB RAM).
*   **Tools (MCP):**
    *   `transcribe_audio(path)`: Returns timestamped text segments.
    *   `summarize_text(text)`: Returns structured markdown.
    *   `save_action_item(task, owner, date)`: Writes to DB.

## 6. Non-Functional Requirements

### 6.1 Privacy & Security
*   **Zero-Exfiltration:** The application MUST NOT have Internet permissions (Android Manifest / Sandbox restriction).
*   **Local Storage:** All audio and DB files stored in the device's protected app sandbox.

### 6.2 Performance & Resource Management
*   **Memory Footprint:** Efficiently manages resources by unloading/loading models (Whisper/Qwen) sequentially.
*   **Context Efficiency:** Implements rolling window summarization to prevent context overflow.
*   **Inference Latency:** 
    *   Transcription: < 0.5x real-time (1 hour audio transcribes in < 30 mins).
    *   Summarization: < 45 seconds per chunk.
*   **Resource Usage:** Total RAM footprint < 1.0 GB. Battery drain < 10% per hour via VAD efficiency.

### 6.3 Reliability
*   **Hallucination Rate:** < 1% syntax errors on JSON outputs (enforced via GBNF).
*   **Crash Recovery:** If the OS kills the app (OOM), it must resume processing from the last checkpoint upon restart.

## 7. UX/UI Flow

1.  **Home Screen:** Clean list of recent meetings with status (Processing, Done). Large "Record" FAB (Floating Action Button).
2.  **Recording Mode:** Minimalist UI. Waveform visualization. "Add Marker" button to flag important moments during recording.
3.  **Review Screen:** Split view. Top: Audio player with timeline. Bottom: Scrollable transcript synced to audio.
4.  **Summary Tab:** Rendered Markdown view of the AI summary. Editable text areas for manual corrections.

## 8. Technical Stack Constraints
*(Derived from System Design)*
*   **Engine:** MLC LLM or llama.cpp (Python/C++ bindings).
*   **Orchestration:** Python (Backend Logic) / Flutter or React Native (Frontend UI).
*   **Database:** SQLite.
*   **Protocol:** Model Context Protocol (MCP) for internal tool communication.

## 9. Roadmap

| Phase | Milestone | Deliverables |
|-------|-----------|--------------|
| **Phase 1** | **MVP Core** | Audio recording, Whisper transcription, Basic Qwen summarization (Text-only output). |
| **Phase 2** | **Agentic Integration** | Implement MCP tools, GBNF constraints, and SQLite Action Item syncing. |
| **Phase 3** | **UX Polish** | Mobile UI, Search, Audio seeking, Export to PDF/Markdown. |
| **Phase 4** | **Expansion** | "Speculative Decoding" speed-up, Calendar integration (read-only). |

## 10. Success Metrics
*   **Accuracy:** >95% accuracy in distinguishing "Action Items" from general chatter.
*   **Speed:** Average user spends < 2 minutes reviewing a 1-hour meeting summary.
*   **Stability:** Zero data loss. Failed chunks are recovered from the queue on app restart.
