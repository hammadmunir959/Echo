import json
import asyncio
from typing import Optional
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from app.utils.event_bus import event_bus
from app.utils.auth_utils import get_organization_id

router = APIRouter()

@router.get("/")
async def stream_events(
    request: Request,
    node_id: Optional[str] = Query(None),
    station_id: Optional[str] = Query(None),
    organization_id: str = Depends(get_organization_id)
):
    """
    Server-Sent Events endpoint for real-time dispatch monitoring mapped to tenant.
    """
    async def event_generator():
        q = await event_bus.subscribe()
        try:
            while True:
                if await request.is_disconnected():
                    break
                
                try:
                    event = await asyncio.wait_for(q.get(), timeout=1.0)
                    
                    # Ensure isolation check matches tenant stream filter
                    if event.get("organization_id") != organization_id:
                        continue
                        
                    if node_id and event.get("node_id") != node_id:
                        continue

                    if station_id and event.get("station_id") != station_id:
                        continue
                        
                    yield f"data: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
        finally:
            await event_bus.unsubscribe(q)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
