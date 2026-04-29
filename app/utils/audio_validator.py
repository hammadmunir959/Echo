import re
import io
import soundfile as sf
from fastapi import UploadFile, HTTPException, status
from app.core.config import Settings

class AudioInfo:
    def __init__(self, duration: float, sample_rate: int):
        self.duration = duration
        self.sample_rate = sample_rate

class AudioValidator:
    NODE_ID_REGEX = re.compile(r"^[a-zA-Z0-9_-]{3,64}$")
    ALLOWED_MIME_TYPES = {
        "audio/wav", "audio/x-wav", "audio/wave",
        "audio/webm", "audio/ogg", "audio/mpeg", "audio/mp3"
    }

    @classmethod
    def validate(cls, file: UploadFile, node_id: str, settings: Settings) -> AudioInfo:
        # 1. Node ID validation
        if not cls.NODE_ID_REGEX.match(node_id):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid node_id: {node_id}. Must be 3-64 chars (alphanumeric, -, _)"
            )

        # 2. MIME type validation
        if file.content_type not in cls.ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unsupported format: {file.content_type}"
            )

        return cls._validate_media(file, settings)

    @staticmethod
    def _validate_media(file: UploadFile, settings: Settings) -> AudioInfo:
        # Seek to start just in case
        file.file.seek(0)
        content = file.file.read()
        
        if len(content) > settings.max_audio_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large: {len(content)} bytes"
            )

        if len(content) == 0:
             raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Empty audio file"
            )

        try:
            # Soundfile check for duration
            with sf.SoundFile(io.BytesIO(content)) as f:
                duration = len(f) / f.samplerate
                if duration > settings.max_audio_duration_seconds:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=f"Audio too long: {duration:.1f}s (max {settings.max_audio_duration_seconds}s)"
                    )
                return AudioInfo(duration=duration, sample_rate=f.samplerate)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid or corrupt audio file: {str(e)}"
            )
        finally:
            file.file.seek(0)
