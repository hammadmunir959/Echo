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
    beam_size: int = 5
    compute_type: str = "int8"            # int8 / float16 / bfloat16
    device: str = "cpu"                   # cpu / cuda
    
    # Advanced Transcription Options
    whisper_language: str | None = None   # Hardcode to "en" for speed/accuracy if known
    initial_prompt: str | None = None     # Use for context/jargon
    vad_filter: bool = True               # Enable Voice Activity Detection
    vad_min_silence_duration_ms: int = 500
    word_timestamps: bool = True

    # LLM Settings (llama.cpp)
    llm_model_path: Path | None = None    # Path to GGUF model
    llm_n_ctx: int = 4096
    llm_n_gpu_layers: int = 0             # Set > 0 for GPU offloading
    llm_temperature: float = 0.1
    llm_max_tokens: int = 512

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
