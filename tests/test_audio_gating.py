import unittest
import sys
import os
import audioop
import collections

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.config import Config
# Mock audio_stream dependency on distributed_tasks if needed, 
# but for logic testing we just need the class structure or manually replicate the logic
# actually let's import the class but mock the VAD and Pyaudio

class MockVad:
    def is_speech(self, chunk, rate):
        return True

class TestAudioGating(unittest.TestCase):
    def setUp(self):
        self.ENERGY_THRESHOLD = 500
        Config.ENERGY_THRESHOLD = 500
        
    def test_silence_rejection(self):
        """Test that low energy audio is rejected."""
        # Generate 30ms of silence (zeros)
        # 16000Hz * 0.03s = 480 samples. 16-bit = 2 bytes/sample.
        silence = b'\x00' * 480 * 2 
        
        rms = audioop.rms(silence, 2)
        print(f"Silence RMS: {rms}")
        
        self.assertTrue(rms < self.ENERGY_THRESHOLD, "Silence should have RMS below threshold")
        
    def test_loud_audio_acceptance(self):
        """Test that loud audio passes the energy check."""
        # Generate random noise (loud)
        # 0xFF is -127 or 127 in signed byte? 
        # Let's verify with actual bytes
        loud_byte = b'\x7F\xFF' # Max amplitude approx
        loud_chunk = loud_byte * 480
        
        rms = audioop.rms(loud_chunk, 2)
        print(f"Loud RMS: {rms}")
        
        self.assertTrue(rms > self.ENERGY_THRESHOLD, "Loud audio should have RMS above threshold")

if __name__ == '__main__':
    unittest.main()
