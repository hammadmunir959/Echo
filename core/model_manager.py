import os
import logging
from huggingface_hub import hf_hub_download
from core.config import Config

logger = logging.getLogger("EchoModelManager")

class ModelManager:
    """
    Handles downloading and path management for AI models (GGUF versions).
    POTATO STACK: reverted to GGUF (llama.cpp) as it is robust on non-AVX.
    """

    @staticmethod
    def get_whisper_model_path():
        return Config.WHISPER_MODEL

    @staticmethod
    def get_slm_model_path():
        """
        Ensures the Qwen GGUF model is present in the local `models/` dir.
        Returns the absolute path.
        """
        # Target path
        model_name = "Qwen/Qwen2-0.5B-Instruct-GGUF"
        filename = "qwen2-0_5b-instruct-q4_k_m.gguf" 
        repo_id = "Qwen/Qwen2-0.5B-Instruct-GGUF"
        
        target_path = Config.MODELS_DIR / filename
        
        if not target_path.exists():
            logger.info(f"Downloading SLM model: {filename}...")
            try:
                downloaded_path = hf_hub_download(
                    repo_id=repo_id,
                    filename=filename,
                    local_dir=Config.MODELS_DIR,
                    local_dir_use_symlinks=False
                )
                logger.info(f"Model downloaded to: {downloaded_path}")
            except Exception as e:
                logger.error(f"Failed to download model: {e}")
                raise
        
        return str(target_path)

model_manager = ModelManager()
