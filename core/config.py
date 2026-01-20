import os
import shutil
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("EchoConfig")

class Config:
    # Paths
    # Current file is in core/, so we need the parent of the parent!
    BASE_DIR = Path(__file__).parent.parent.absolute()
    DATABASE_PATH = BASE_DIR / "database" / "echo.db"
    RECORDINGS_DIR = BASE_DIR / "recordings"
    MODELS_DIR = BASE_DIR / "models"
    
    # Model Configurations
    WHISPER_MODEL = os.getenv("ECHO_WHISPER_MODEL", "base.en")
    QWEN_MODEL_NAME = "Qwen/Qwen3-0.6B" # Reference name for ModelManager
    
    # Audio Settings
    CHUNK_DURATION_SECONDS = 30
    VAD_AGRESSIVENESS = 3  # 0-3
    ENERGY_THRESHOLD = 500  # Minimum RMS energy to trigger VAD
    
    # Resilience
    MAX_RETRIES = int(os.getenv("ECHO_MAX_RETRIES", 5))
    
    @classmethod
    def initialize_directories(cls):
        """Ensure all required directories exist."""
        for directory in [cls.RECORDINGS_DIR, cls.MODELS_DIR, cls.DATABASE_PATH.parent]:
            directory.mkdir(parents=True, exist_ok=True)
            logger.info(f"Directory verified: {directory}")

    @classmethod
    def check_dependencies(cls):
        """Verify system dependencies like ffmpeg."""
        if shutil.which("ffmpeg") is None:
            logger.error("FFmpeg not found! Please install it for audio processing.")
            return False
        logger.info("FFmpeg found.")
        return True

# Initialize on import
Config.initialize_directories()
