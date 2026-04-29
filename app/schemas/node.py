from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class NodeOut(BaseModel):
    id: str
    organization_id: str
    station_id: str
    label: Optional[str] = None
    last_seen_at: Optional[datetime] = None
    transcript_count: int = 0

class NodeStats(BaseModel):
    id: str
    organization_id: str
    station_id: str
    transcript_count: int
    last_activity: datetime
