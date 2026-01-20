import wave
import struct
import math
import os

def create_sine_wave(fq, duration, filename):
    # Parameters
    sample_rate = 16000
    n_samples = int(sample_rate * duration)
    
    # Generate wav
    with wave.open(filename, 'w') as obj:
        obj.setnchannels(1) # mono
        obj.setsampwidth(2) # 2 bytes
        obj.setframerate(sample_rate)
        
        for i in range(n_samples):
            value = int(32767.0 * math.sin(2 * math.pi * fq * i / sample_rate))
            data = struct.pack('<h', value)
            obj.writeframesraw(data)

if __name__ == "__main__":
    create_sine_wave(440, 2.0, "tests/dummy.wav")
    print("Dummy audio created: tests/dummy.wav")
