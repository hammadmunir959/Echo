import uvicorn
import argparse
import sys
import os
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from core.config import Config

def start_server(host="0.0.0.0", port=8080, reload=False):
    """Starts the Echo API Server."""
    print(f"--- Starting Echo API Server on http://{host}:{port} ---")
    print("Endpoints:")
    print(f"  POST http://{host}:{port}/api/v1/control/start")
    print(f"  POST http://{host}:{port}/api/v1/control/stop")
    print(f"  GET  http://{host}:{port}/api/v1/data/transcripts")
    print(f"  Docs http://{host}:{port}/docs")
    
    # Use the modular API app factory via string reference
    uvicorn.run("api.app:app", host=host, port=port, reload=reload)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Echo API Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8080, help="Port to bind to")
    parser.add_argument("--dev", action="store_true", help="Enable reload mode")
    
    args = parser.parse_args()
    
    start_server(host=args.host, port=args.port, reload=args.dev)
