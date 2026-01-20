from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import time
import threading

from database.db_manager import db_manager
from core.audio_stream import audio_stream

router = APIRouter()

# Models
class ControlResponse(BaseModel):
    status: str
    message: str
    meeting_id: Optional[int] = None

# State (This global state is a bit fragile for a truly distributed app, 
# but for the "Capture Node" part of the API, it's acceptable for now)
CURRENT_MEETING_ID = None

@router.post("/start", response_model=ControlResponse)
def start_recording():
    global CURRENT_MEETING_ID
    
    if audio_stream.is_running:
        return {"status": "error", "message": "Already recording", "meeting_id": CURRENT_MEETING_ID}

    # Create Meeting
    with db_manager.get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO meetings (title, audio_path) VALUES (?, ?)",
            (f"API Session {time.strftime('%Y-%m-%d %H:%M')}", "live_stream")
        )
        CURRENT_MEETING_ID = cursor.lastrowid

    # Start Audio Stream in background thread
    # Note: In a pure distributed model, we might send a message to a capture worker,
    # but `audio_stream` is local to the capture node, so this is correct.
    t = threading.Thread(target=audio_stream.start, args=(CURRENT_MEETING_ID,))
    t.daemon = True
    t.start()
    
    return {"status": "success", "message": "Recording started", "meeting_id": CURRENT_MEETING_ID}

@router.post("/stop", response_model=ControlResponse)
def stop_recording():
    if not audio_stream.is_running:
        return {"status": "error", "message": "Not recording"}
    
    audio_stream.stop()
    return {"status": "success", "message": "Recording stopped"}
