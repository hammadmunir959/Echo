import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Database
    postgres_dsn: str = ""

    # Storage
    audio_dir: Path = Path("data/audio")
    models_dir: Path = Path("assets/models")
    
    # Logging
    log_dir: Path = Path("logs")
    log_level: str = "INFO"

    # Whisper
    whisper_model: str = "base"           # tiny / base / small / medium
    transcription_workers: int = 4        # concurrent Whisper threads (tune per RAM)

    # Ingest limits
    max_audio_duration_seconds: int = 60
    max_audio_size_bytes: int = 10_485_760   # 10 MB

    # API
    api_key: str = "echo_hq_key"

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_prefix="ECHO_",
        extra="ignore"
    )

    def initialize_directories(self):
        """Ensure all required directories exist."""
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.models_dir.mkdir(parents=True, exist_ok=True)

settings = Settings()
settings.initialize_directories()

def get_settings():
    return settings
