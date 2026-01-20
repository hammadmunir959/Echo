import sys
import time
import logging
import wave
import pyaudio
import os
import ctypes
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from llama_cpp import Llama, LlamaGrammar
from core.model_manager import model_manager
from core.transcriber import transcriber

# Silence ALSA/Jack error spam
ERROR_HANDLER_FUNC = ctypes.CFUNCTYPE(None, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p)
def py_error_handler(filename, line, function, err, fmt):
    pass
c_error_handler = ERROR_HANDLER_FUNC(py_error_handler)

try:
    asound = ctypes.cdll.LoadLibrary('libasound.so.2')
    asound.snd_lib_error_set_handler(c_error_handler)
except:
    pass

# Configure logging to be minimal
logging.basicConfig(level=logging.WARNING, format='%(message)s')

def record_audio(duration=5, filename="tests/assets/test_record.wav"):
    """Records a short audio clip from the microphone."""
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000
    
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
    
    print(f"--- Recording for {duration} seconds... Speak now! ---")
    frames = []
    
    for _ in range(0, int(RATE / CHUNK * duration)):
        data = stream.read(CHUNK)
        frames.append(data)
        
    print("Done recording.")
    
    stream.stop_stream()
    stream.close()
    p.terminate()
    
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    wf = wave.open(filename, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()
    return filename

def chat_loop():
    print("\n" + "="*40)
    print("   ECHO INTERACTIVE TEST (CLEAN MODE)   ")
    print("="*40)
    print("Commands:")
    print("  /voice : Record audio (5s) to test Whisper")
    print("  exit   : Close the session")
    print("-" * 40)
    
    # 1. Load Model logic
    try:
        model_path = model_manager.get_slm_model_path()
        print(f"> Loading Qwen Model... ", end="", flush=True)
        llm = Llama(
            model_path=model_path,
            n_ctx=4096,
            n_threads=4,
            verbose=False,
            chat_format="chatml"
        )
        print("Done! 🧠")
        
        print("> Pre-loading Whisper... ", end="", flush=True)
        transcriber.load_model()
        print("Done! 👂")
        
    except Exception as e:
        print(f"\n[ERROR] Loading models: {e}")
        return

    # 2. JSON Grammar (GBNF)
    json_grammar_str = r'''
    root   ::= object
    object ::= "{" space ( pair ( "," space pair )* )? "}"
    pair   ::= string ":" space value
    value  ::= string | number | object | array | "true" | "false" | "null"
    array  ::= "[" space ( value ( "," space value )* )? "]"
    string ::= "\"" ( [^"\\\x00-\x1f] | "\\" ( ["\\/bfnrt] | "u" [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F] ) )* "\""
    number ::= "-"? ( "0" | [1-9] [0-9]* ) ( "." [0-9]+ )? ( [eE] [+-]? [0-9]+ )?
    space  ::= [ \t\n\r]*
    '''
    
    grammar = LlamaGrammar.from_string(json_grammar_str)

    # 3. Chat History
    messages = [
        {"role": "system", "content": "You are Echo, a helpful assistant. You MUST ALWAYS respond in valid JSON format."}
    ]

    # 4. REPL Loop
    while True:
        try:
            print("\n" + "-"*10)
            user_input = input("You: ")
            
            if user_input.lower() in ["exit", "quit"]:
                break
            
            # VOICE MODE
            if user_input.lower() == "/voice":
                temp_audio = record_audio(duration=5)
                
                print("Whisper: Transcription running...", end="", flush=True)
                w_start = time.time()
                text, _ = transcriber.transcribe(temp_audio)
                w_end = time.time()
                
                print(f"\rWhisper heard: \"{text}\" ({w_end - w_start:.2f}s)")
                
                if not text.strip():
                    print("Whisper didn't hear anything. Try again.")
                    continue
                user_input = text
            
            messages.append({"role": "user", "content": user_input})
            
            print("Echo: ", end="", flush=True)
            
            start_time = time.time()
            first_token_time = None
            token_count = 0
            
            response_stream = llm.create_chat_completion(
                messages=messages,
                stream=True,
                max_tokens=512,
                temperature=0.2,
                grammar=grammar
            )
            
            full_response = ""
            for chunk in response_stream:
                if "content" in chunk["choices"][0]["delta"]:
                    text = chunk["choices"][0]["delta"]["content"]
                    if first_token_time is None:
                        first_token_time = time.time()
                    print(text, end="", flush=True)
                    full_response += text
                    token_count += 1
            
            end_time = time.time()
            total_time = end_time - start_time
            ttft = (first_token_time - start_time) if first_token_time else 0
            tps = token_count / total_time if total_time > 0 else 0
            
            print(f"\n[⏱️ Brain: {total_time:.2f}s | TTFT: {ttft:.2f}s | TPS: {tps:.2f} t/s]")
            
            messages.append({"role": "assistant", "content": full_response})
            
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"\n[ERROR]: {e}")

if __name__ == "__main__":
    chat_loop()
