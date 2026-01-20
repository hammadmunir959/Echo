# 🚀 Echo API Robustness & Feature Roadmap

This document outlines the strategy to transition `api/main.py` from a local control interface to a **Commercial-Grade REST & Real-Time API**.

## 1. Security & Access Control (The Gatekeeper)
Currently, the API is open. For a professional deployment, we must secure it.
- [ ] **API Key Authentication**: Middleware to check `X-API-Key` headers.
- [ ] **Role-Based Access (RBAC)**: Distinguish between `admin` (can delete) and `viewer` (read-only).
- [ ] **Rate Limiting**: Use `slowapi` or Redis to limit requests (e.g., 60 req/min) to prevent abuse.

## 2. Capability Expansion
Transform Echo from a "Listener" to a "Platform".

### A. Real-Time Streaming (WebSockets)
Instead of polling `/data/transcripts`, the client should receive updates instantly.
- **Endpoint**: `ws://api/meetings/{id}/stream`
- **Feature**: Push `partial_transcript` tokens as Whisper decodes them (low latency feedback).
- **Benefit**: frontend builds a "Live Captions" UI.

### B. File Upload & Batch Processing
Allow processing of pre-recorded files (e.g., Zoom/Teams recordings).
- **Endpoint**: `POST /upload` (Multipart/Form-Data).
- **Flow**: Upload -> S3/MinIO -> Dispatch Celery Task -> Return `task_id` for polling.

### C. Advanced Search & Filtering
Replace simple `limit` with a powerful query engine.
- **Filters**: `GET /data/action-items?owner=John&status=open&date_after=2024-01-01`
- **Full-Text Search**: Integrate **FTS5** (SQLite) or **Meilisearch** to search inside transcript content.
    - `GET /search?q="quarterly predictions"`

## 3. Professional Standards (DX)
Make the API a joy to consume for developers.

- **Versioning**: Prefix all endpoints with `/v1`.
    - Allows breaking changes in `/v2` without disrupting existing clients.
- **Standardized Error Responses**:
    ```json
    {
      "error": {
        "code": "RESOURCE_NOT_FOUND",
        "message": "Meeting ID 123 does not exist",
        "doc_url": "..."
      }
    }
    ```
- **HATEOAS / Pagination**: Return `next_page_url` and `total_count` in metadata.

## 4. Proposed Implementation Steps

### Step 1: Structural Refactor
- Move `api/main.py` to `api/app.py` and creating `api/routers/` (split `control`, `data`, `auth`).
- Introduce `GlobalExceptionHandler`.

### Step 2: Security Layer
- Implement `api/security.py` with `APIKeyHeader` scheme.

### Step 3: WebSocket Layer
- Add `FastAPI.websocket` endpoint.
- Connect it to a Redis Pub/Sub channel to broadcast transcript events from workers.

### Step 4: Search Engine
- Enable SQLite FTS5 for the `transcripts` table.
- Create a dedicated `/search` endpoint.
