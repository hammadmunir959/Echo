#!/bin/bash

# Echo Distributed Launcher
echo "Starting Echo Distributed System..."

# Get project root (one level up from bin)
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT" || exit 1

echo "WorkDir: $PROJECT_ROOT"

# Use venv if available
if [ -d "$PROJECT_ROOT/venv" ]; then
    PYTHON="$PROJECT_ROOT/venv/bin/python3"
    echo "[✓] Using Virtual Environment: $PYTHON"
else
    PYTHON="python3"
    echo "[!] Virtual Environment NOT found. Using system python."
fi

# 1. Start Redis in Background
if pgrep -x "redis-server" > /dev/null
then
    echo "[✓] Redis is already running."
else
    echo "[!] Starting Redis Server..."
    redis-server --daemonize yes
fi

# 2. Start API Server (Background)
echo "[!] Starting API Server..."
$PYTHON runners/api_server.py --port 8080 &

# 3. Start Transcription Worker (STT)
echo "[!] Starting Transcription Worker..."
$PYTHON runners/worker_stt.py &

# 4. Start Summarization Worker (LLM)
echo "[!] Starting Summarization Worker..."
$PYTHON runners/worker_llm.py &

echo "--- System is UP ---"
echo "API: http://localhost:8080"
echo "Logs: Integrated into this terminal (Ctrl+C to stop all)"
wait
