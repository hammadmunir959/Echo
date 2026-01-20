from fastapi import FastAPI
from contextlib import asynccontextmanager
import logging

from database.db_manager import db_manager
from core.audio_stream import audio_stream
from api.v1.router import api_router

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("EchoAPI")

# Lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("API Startup: Initializing DB...")
    db_manager.init_db()
    yield
    # Shutdown
    logger.info("API Shutdown: Stopping background workers...")
    audio_stream.stop()

from fastapi import FastAPI, Depends
from api.core.security import get_api_key

# ... imports ...

# App Factory
def create_app() -> FastAPI:
    app = FastAPI(title="Echo Agent API", version="2.0.0", lifespan=lifespan)
    
    # Include V1 Router (Secured)
    app.include_router(api_router, prefix="/api/v1", dependencies=[Depends(get_api_key)])
    
    # Legacy Support / Redirects (Optional, or just expose /api/v1)
    # For now, we will expose the new structure strictly.
    
    @app.get("/")
    def health_check():
        return {"status": "ok", "service": "Echo Agent API v2.0", "docs": "/docs"}
        
    return app

app = create_app()
