from pydantic import BaseModel
from datetime import datetime

class IngestResponse(BaseModel):
    status: str
    node_id: str
    organization_id: str
    station_id: str
    received_at: datetime
    queue_depth: int

class IngestError(BaseModel):
    detail: str
    code: str
