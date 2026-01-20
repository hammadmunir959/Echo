from core.audio_stream import audio_stream
import time
import threading

def test_audio():
    print("--- Testing Audio Injection (VAD Gated) ---")
    print("Please speak into the microphone...")
    print("Press Ctrl+C to stop manually, or wait 40 seconds.")

    # Run audio stream in a separate thread so we can kill it
    t = threading.Thread(target=audio_stream.start)
    t.daemon = True
    t.start()

    try:
        # Let it run for 40 seconds to trigger at least one save (30s threshold)
        for i in range(40):
            print(f"Recording... {i}/40s", end='\r')
            time.sleep(1)
        print("\nStopping stream...")
        audio_stream.stop()
        t.join(timeout=2)
        
    except KeyboardInterrupt:
        audio_stream.stop()
    
    print("Test finished. Check 'recordings/' folder and 'task_queue' table.")

if __name__ == "__main__":
    test_audio()
