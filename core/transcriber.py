import logging
import os
from faster_whisper import WhisperModel
from core.config import Config

logger = logging.getLogger("EchoTranscriber")

class Transcriber:
    def __init__(self):
        self.model = None
    
    def load_model(self):
        """Loads Whisper model into memory."""
        if self.model is None:
            logger.info(f"Loading Whisper model: {Config.WHISPER_MODEL}")
            # Run on CPU with INT8 by default for compatibility
            self.model = WhisperModel(Config.WHISPER_MODEL, device="cpu", compute_type="int8")
            logger.info("Whisper model loaded.")

    def unload_model(self):
        """Explicitly unloads model to free RAM."""
        if self.model:
            del self.model
            self.model = None
            logger.info("Whisper model unloaded.")

    def transcribe(self, audio_path):
        """
        Transcribes the audio file.
        Returns: full_text (str), segments (list of dicts)
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        self.load_model()
        
        segments, info = self.model.transcribe(audio_path, beam_size=5)
        logger.info(f"Detected language '{info.language}' with probability {info.language_probability}")

        # Collect segments
        segment_list = []
        full_text = []
        
        for segment in segments:
            seg_data = {
                "start": segment.start,
                "end": segment.end,
                "text": segment.text.strip()
            }
            segment_list.append(seg_data)
            full_text.append(segment.text.strip())
        
        # We unload immediately after use to save memory (Sequential Loading Strategy)
        self.unload_model()
        
        return " ".join(full_text), segment_list

transcriber = Transcriber()
