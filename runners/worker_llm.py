import subprocess
import sys
import os
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

def start_worker():
    """Starts a Celery worker dedicated to summarization (LLM)."""
    print("--- Starting Echo Summarization Worker ---")
    cmd = [
        "celery", "-A", "core.celery_app", "worker",
        "-l", "INFO",
        "-c", "1",
        "-n", "worker_llm@%h"
    ]
    subprocess.run(cmd)

if __name__ == "__main__":
    start_worker()
