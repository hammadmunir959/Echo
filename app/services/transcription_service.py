import threading
import structlog
from pathlib import Path
from faster_whisper import WhisperModel
from typing import NamedTuple, List, Dict, Any

logger = structlog.get_logger("transcription_service")
_thread_local = threading.local()

class TranscriptResult(NamedTuple):
    text: str
    segments: List[Dict[str, Any]]
    language: str
    language_probability: float
    duration: float

class TranscriptionService:
    def __init__(self, model_name: str, models_dir: Path, device: str = "cpu", compute_type: str = "int8"):
        self.model_name = model_name
        self.models_dir = models_dir
        self.device = device
        self.compute_type = compute_type

    def ensure_model_ready(self):
        """
        Triggers model download/verification so the system is ready before 
        the first request. Call this during app startup.
        """
        logger.info("Checking Whisper model for readiness", model=self.model_name, dir=str(self.models_dir))
        _ = WhisperModel(
            self.model_name,
            device="cpu", 
            compute_type="int8",
            download_root=str(self.models_dir),
            local_files_only=True
        )
        logger.info("Model is verified and ready", model=self.model_name)

    def _get_model(self) -> WhisperModel:
        """
        Each thread gets its own Whisper instance to enable true parallelism 
        without lock contention.
        """
        if not hasattr(_thread_local, "model"):
            logger.info("Loading Whisper model on thread", model=self.model_name, thread=threading.current_thread().name)
            _thread_local.model = WhisperModel(
                self.model_name, 
                device=self.device, 
                compute_type=self.compute_type,
                download_root=str(self.models_dir),
                local_files_only=True
            )
        return _thread_local.model

    def transcribe(self, audio_path: str) -> TranscriptResult:
        model = self._get_model()
        logger.info("Transcribing audio file", path=audio_path)
        
        segments, info = model.transcribe(
            audio_path, 
            beam_size=5, 
            word_timestamps=True
        )
        
        full_text = []
        segment_list = []
        
        for segment in segments:
            full_text.append(segment.text.strip())
            segment_list.append({
                "start": segment.start,
                "end": segment.end,
                "text": segment.text.strip(),
                "words": [
                    {"word": w.word, "start": w.start, "end": w.end, "probability": w.probability}
                    for w in (segment.words or [])
                ]
            })
            
        return TranscriptResult(
            text=" ".join(full_text),
            segments=segment_list,
            language=info.language,
            language_probability=info.language_probability,
            duration=info.duration
        )
