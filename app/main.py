import logging
import asyncio
from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.db.database import init_db
from app.api.router import api_router
from app.services.transcription_service import TranscriptionService
from app.services.pipeline import pipeline_worker
from app.utils.event_bus import event_bus

# Setup logging
setup_logging()
logger = logging.getLogger("EchoHQ")

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    loop = asyncio.get_event_loop()
    
    # 1. Initialize Directories & Permissions
    logger.info("Initializing system directories...")
    settings.initialize_directories()
    
    # 2. Initialize DB
    logger.info("Connecting to PostgreSQL and verifying schemas...")
    init_db()
    
    # 3. AI Model Readiness
    transcriber = TranscriptionService(
        model_name=settings.whisper_model,
        models_dir=settings.models_dir
    )
    # Run model verification in a thread to keep the event loop from hanging
    # while potentially downloading large files.
    logger.info("Performing AI model readiness check...")
    await loop.run_in_executor(None, transcriber.ensure_model_ready)
    
    # 4. Pipeline setup
    queue: asyncio.Queue = asyncio.Queue()
    app.state.queue = queue
    
    # Start N workers as configured
    logger.info(f"Starting {settings.transcription_workers} transcription workers...")
    workers = [
        asyncio.create_task(pipeline_worker(queue, settings, transcriber))
        for _ in range(settings.transcription_workers)
    ]
    
    logger.info("--- ECHO HQ SYSTEM FULLY INITIALIZED & READY ---")
    yield
    
    # 3. Shutdown logic
    logger.info("Shutting down workers...")
    for w in workers:
        w.cancel()
    
    # Wait for cancel to propagate
    await asyncio.gather(*workers, return_exceptions=True)
    logger.info("Echo HQ Shutdown complete.")

def create_app() -> FastAPI:
    app = FastAPI(
        title="Echo HQ Dispatch Transcription",
        version="3.0.0",
        lifespan=lifespan
    )
    
    # Include routers
    app.include_router(api_router, prefix="/api/v1")
    
    @app.get("/health")
    def health_check():
        return {"status": "ok", "system": "Echo HQ v3.0"}
        
    return app

app = create_app()
