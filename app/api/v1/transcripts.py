from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db.database import get_db_session
from app.utils.auth_utils import get_organization_id
from app.services.transcripts_service import TranscriptsService
from app.schemas.transcript import TranscriptOut
import structlog

logger = structlog.get_logger("api.transcripts")
router = APIRouter()

@router.get("/", response_model=List[TranscriptOut])
def list_org_transcripts(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db_session),
    organization_id: str = Depends(get_organization_id)
):
    """List all transcripts for the current organization."""
    results = TranscriptsService.get_by_org(db, organization_id, limit=limit)
    return [TranscriptOut.model_validate(r) for r in results]

@router.get("/station/{station_id}", response_model=List[TranscriptOut])
def list_station_transcripts(
    station_id: str,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db_session),
    organization_id: str = Depends(get_organization_id)
):
    """List all transcripts for a specific station within the organization."""
    results = TranscriptsService.get_by_station(db, organization_id, station_id, limit=limit)
    return [TranscriptOut.model_validate(r) for r in results]

@router.get("/node/{node_id}", response_model=List[TranscriptOut])
def list_node_transcripts(
    node_id: str,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db_session),
    organization_id: str = Depends(get_organization_id)
):
    """List all transcripts for a specific node within the organization."""
    results = TranscriptsService.get_by_node(db, organization_id, node_id, limit=limit)
    return [TranscriptOut.model_validate(r) for r in results]

@router.get("/search", response_model=List[TranscriptOut])
def search_transcripts(
    q: str = Query(..., min_length=1),
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db_session),
    organization_id: str = Depends(get_organization_id)
):
    """Search transcripts by text content using fuzzy matching (ILIKE)."""
    results = TranscriptsService.search(db, organization_id, q, limit=limit)
    return [TranscriptOut.model_validate(r) for r in results]

@router.get("/{transcript_id}", response_model=TranscriptOut)
def get_transcript(
    transcript_id: int,
    db: Session = Depends(get_db_session),
    organization_id: str = Depends(get_organization_id)
):
    """Get a single transcript by ID."""
    from sqlalchemy import select
    from app.models.dbmodels import Transcript
    stmt = select(Transcript).where(
        Transcript.id == transcript_id, 
        Transcript.organization_id == organization_id
    )
    result = db.execute(stmt).scalar_one_or_none()
    
    if not result:
        raise HTTPException(status_code=404, detail="Transcript not found")
        
    return TranscriptOut.model_validate(result)
