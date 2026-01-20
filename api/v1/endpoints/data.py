from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
from database.db_manager import db_manager

router = APIRouter()

# Models
class ActionItem(BaseModel):
    id: int
    meeting_id: Optional[int]
    description: str
    owner: Optional[str]
    status: str

class Transcript(BaseModel):
    id: int
    meeting_id: Optional[int]
    raw_text: str

@router.get("/transcripts", response_model=List[Transcript])
def get_transcripts(limit: int = 10):
    with db_manager.get_connection() as conn:
        rows = conn.execute("SELECT id, meeting_id, raw_text FROM transcripts ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(row) for row in rows]

@router.get("/action-items", response_model=List[ActionItem])
def get_action_items(limit: int = 10):
    with db_manager.get_connection() as conn:
        rows = conn.execute("SELECT * FROM action_items ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(row) for row in rows]

@router.get("/search", response_model=List[Transcript])
def search_transcripts(q: str, limit: int = 10):
    """
    Full Text Search using SQLite FTS5.
    Query examples: "budget", "quarterly AND goals", "deploy*"
    """
    with db_manager.get_connection() as conn:
        # Use FTS MATCH operator
        # We assume FTS table exists (created in db_manager)
        try:
            # We select from the VIRTUAL table or join with main
            # Simple select from main filtering by FTS match rowid
            query = """
                SELECT t.id, t.meeting_id, snippet(transcripts_fts, 0, '<b>', '</b>', '...', 64) as raw_text
                FROM transcripts t
                JOIN transcripts_fts fts ON t.id = fts.rowid
                WHERE fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """
            rows = conn.execute(query, (q, limit)).fetchall()
            
            # Map 'raw_text' in result to snippet for highlighting
            return [
                {
                    "id": row['id'], 
                    "meeting_id": row['meeting_id'], 
                    "raw_text": row['raw_text'] # This will be the snippet
                } 
                for row in rows
            ]
        except Exception as e:
            # Fallback if FTS not available or query error
            print(f"Search Error: {e}")
            return []
