from datetime import datetime
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, Depends, Request
from app.core.config import Settings, get_settings
from app.utils.auth_utils import get_organization_id
from app.utils.audio_validator import AudioValidator
from app.services.storage_service import StorageService
from app.services.pipeline import TranscriptionJob
from app.schemas.ingest import IngestResponse

router = APIRouter()

@router.post("/audio", response_model=IngestResponse, status_code=202)
async def ingest_audio(
    request: Request,
    audio: UploadFile = File(...),
    node_id: str = Form(...),
    station_id: str = Form(...),
    recorded_at: Optional[datetime] = Form(None),
    settings: Settings = Depends(get_settings),
    organization_id: str = Depends(get_organization_id)
):
    """
    Receives an audio chunk from a node, validates it, saves it, 
    and enqueues it for transcription.
    """
    received_at = datetime.now()
    
    # 1. Validate
    _info = AudioValidator.validate(audio, node_id, settings)
    
    audio.file.seek(0)
    file_bytes = audio.file.read()
    
    # 2. Save to storage
    audio_path = StorageService.save(file_bytes, node_id, organization_id, station_id, received_at, settings)
    
    # 3. Enqueue for pipeline
    job = TranscriptionJob(
        node_id=node_id,
        organization_id=organization_id,
        station_id=station_id,
        received_at=received_at,
        recorded_at=recorded_at,
        audio_path=audio_path
    )
    
    queue_depth = request.app.state.queue.qsize()
    await request.app.state.queue.put(job)
    
    return IngestResponse(
        status="queued",
        node_id=node_id,
        organization_id=organization_id,
        station_id=station_id,
        received_at=received_at,
        queue_depth=queue_depth + 1
    )
