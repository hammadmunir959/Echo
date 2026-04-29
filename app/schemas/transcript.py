from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class TranscriptOut(BaseModel):
    model_config = {"from_attributes": True}
    
    id: int
    node_id: str
    organization_id: str
    station_id: str
    received_at: datetime
    recorded_at: Optional[datetime] = None
    duration_seconds: float
    raw_text: str
    audio_path: str
    language: Optional[str] = None

class TranscriptPage(BaseModel):
    items: List[TranscriptOut]
    total: int
    limit: int
    offset: int

class SearchResult(BaseModel):
    id: int
    node_id: str
    organization_id: str
    station_id: str
    received_at: datetime
    snippet: str
    audio_path: str
