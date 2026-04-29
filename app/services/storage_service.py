import uuid
from pathlib import Path
from datetime import datetime
from app.core.config import Settings

class StorageService:
    @staticmethod
    def save(file_bytes: bytes, node_id: str, organization_id: str, station_id: str, received_at: datetime, settings: Settings) -> Path:
        """
        Saves audio to: data/audio/{organization_id}/{station_id}/{node_id}/{YYYY-MM-DD}/{ts}.wav
        """
        date_str = received_at.strftime("%Y-%m-%d")
        ts_str = received_at.strftime("%Y%m%dT%H%M%S")
        uid = uuid.uuid4().hex[:6]
        
        dest_dir = settings.audio_dir / organization_id / station_id / node_id / date_str
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"{ts_str}_{uid}.wav"
        dest_path = dest_dir / filename
        
        with open(dest_path, "wb") as f:
            f.write(file_bytes)
            
        # Return relative path from settings.audio_dir for DB storage
        return dest_path.relative_to(settings.audio_dir)
