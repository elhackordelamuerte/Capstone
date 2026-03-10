import sys
import wave
import threading
import time
from pathlib import Path

# Note: pyaudio might require system packages to be installed
try:
    import pyaudio
except ImportError:
    print("PyAudio not installed. Please install it with 'pip install pyaudio' and required system dependencies.")
    sys.exit(1)

import config

class AudioRecorder:
    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.stream = None
        self.frames = []
        self.is_recording = False
        self.record_thread = None
        
        # We need paInt16 mapped
        self.format = pyaudio.paInt16

    def start(self):
        if self.is_recording:
            return
            
        self.frames = []
        self.is_recording = True
        
        self.stream = self.p.open(format=self.format,
                                  channels=config.CHANNELS,
                                  rate=config.RATE,
                                  input=True,
                                  frames_per_buffer=config.CHUNK)
                                  
        self.record_thread = threading.Thread(target=self._record_loop)
        self.record_thread.start()
        print("Recording started...")

    def _record_loop(self):
        while self.is_recording:
            try:
                data = self.stream.read(config.CHUNK, exception_on_overflow=False)
                self.frames.append(data)
            except Exception as e:
                print(f"Error reading audio stream: {e}")
                break

    def stop(self, output_path: Path):
        if not self.is_recording:
            return
            
        self.is_recording = False
        if self.record_thread:
            self.record_thread.join()
            
        self.stream.stop_stream()
        self.stream.close()
        
        # Save to WAV
        output_path.parent.mkdir(parents=True, exist_ok=True)
        wf = wave.open(str(output_path), 'wb')
        wf.setnchannels(config.CHANNELS)
        wf.setsampwidth(self.p.get_sample_size(self.format))
        wf.setframerate(config.RATE)
        wf.writeframes(b''.join(self.frames))
        wf.close()
        
        print(f"Recording saved to {output_path}")

    def cleanup(self):
        self.p.terminate()
