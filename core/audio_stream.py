import os
import wave
import uuid
import time
import logging
import pyaudio
import webrtcvad
import collections
import audioop
from core.config import Config
from core.distributed_tasks import task_transcribe

logger = logging.getLogger("EchoAudio[WebRTC]")

class AudioStream:
    def __init__(self):
        # Audio Configuration
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 16000
        # WebRTC VAD requires 10, 20, or 30ms frames. 
        # 30ms @ 16000Hz = 480 samples.
        self.CHUNK = 480 
        
        # VAD Configuration
        self.vad = webrtcvad.Vad(Config.VAD_AGRESSIVENESS)
        
        # State Machine & Buffering
        self.p = pyaudio.PyAudio()
        self.stream = None
        self.speech_buffer = [] 
        self.pre_roll = collections.deque(maxlen=50) # ~1.5s (50 * 30ms)
        self.post_roll_counter = 0
        self.POST_ROLL_LIMIT = 60 # ~2.0s (60 * 30ms)
        self.is_running = False
        self.last_save_time = time.time()
        self.meeting_id = None
        
    def _is_speech(self, audio_chunk):
        """Check if chunk contains speech using RMS Energy + WebRTC VAD."""
        try:
            # 1. Energy Check (RMS)
            rms = audioop.rms(audio_chunk, 2) # 2 bytes per sample
            if rms < Config.ENERGY_THRESHOLD:
                return False
                
            # 2. VAD Check
            return self.vad.is_speech(audio_chunk, self.RATE)
        except Exception as e:
            logger.error(f"VAD/RMS Error: {e}")
            return False

    def start(self, meeting_id):
        """Start the continuous recording loop."""
        self.meeting_id = meeting_id
        
        self.stream = self.p.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE,
            input=True,
            frames_per_buffer=self.CHUNK
        )
        
        self.is_running = True
        logger.info("Audio stream started (WebRTC VAD Listening...)")
        
        try:
            while self.is_running:
                data = self.stream.read(self.CHUNK, exception_on_overflow=False)
                
                is_speech = self._is_speech(data)
                
                if is_speech:
                    # Start or Continue recording
                    if not self.speech_buffer:
                        # Append Pre-roll
                        self.speech_buffer.extend(list(self.pre_roll))
                        self.pre_roll.clear()
                    
                    self.speech_buffer.append(data)
                    self.post_roll_counter = self.POST_ROLL_LIMIT
                else:
                    # Silence - Handle Post-roll
                    if self.post_roll_counter > 0:
                        self.speech_buffer.append(data)
                        self.post_roll_counter -= 1
                    else:
                        # Real silence - fill pre-roll buffer
                        self.pre_roll.append(data)
                
                # Rolling Buffer Management
                current_time = time.time()
                elapsed = current_time - self.last_save_time
                
                # Save condition: 30s elapsed AND we have some active data
                if elapsed >= Config.CHUNK_DURATION_SECONDS:
                    if len(self.speech_buffer) > (self.POST_ROLL_LIMIT + 50): # Ensure it's not JUST roll
                        self.save_chunk()
                    else:
                        self.last_save_time = current_time
                        
        except KeyboardInterrupt:
            self.stop()
        except Exception as e:
            logger.error(f"Audio loop error: {e}")
            self.stop()

    def save_chunk(self):
        """Flushes the buffer to a WAV file and enqueues it."""
        filename = f"chunk_{uuid.uuid4().hex}.wav"
        filepath = Config.RECORDINGS_DIR / filename
        
        logger.info(f"Saving audio chunk: {filename} ({len(self.speech_buffer)} frames)")
        
        wf = wave.open(str(filepath), 'wb')
        wf.setnchannels(self.CHANNELS)
        wf.setsampwidth(self.p.get_sample_size(self.FORMAT))
        wf.setframerate(self.RATE)
        wf.writeframes(b''.join(self.speech_buffer))
        wf.close()
        
        # Dispatch to Celery
        task_transcribe.delay(str(filepath), self.meeting_id)
        
        # Reset Logic
        self.speech_buffer = []
        self.last_save_time = time.time()

    def stop(self):
        """Stops the stream safely."""
        logger.info("Stopping audio stream...")
        self.is_running = False
        
        # Give the loop time to exit gracefully
        time.sleep(0.5) 
        
        try:
            if self.stream:
                if self.stream.is_active():
                    self.stream.stop_stream()
                self.stream.close()
            self.p.terminate()
        except Exception as e:
            logger.error(f"Error checking closing stream: {e}")
            
        logger.info("Audio stream stopped.")

# Global instance
audio_stream = AudioStream()
