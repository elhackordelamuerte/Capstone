import os
from pathlib import Path

try:
    from faster_whisper import WhisperModel
except ImportError:
    print("faster_whisper not installed.")

import config

class Transcriber:
    def __init__(self, language=None):
        self.model_size = config.WHISPER_MODEL
        self.compute_type = config.COMPUTE_TYPE
        self.language = language # e.g., 'fr', 'en'
        
        print(f"Loading faster-whisper model: {self.model_size} (CPU, {self.compute_type})")
        # Run on CPU for Raspberry Pi
        self.model = WhisperModel(self.model_size, device="cpu", compute_type=self.compute_type)
        print("Whisper model loaded.")

    def transcribe(self, audio_path: Path, output_text_path: Path) -> str:
        print(f"Starting transcription for {audio_path}...")
        
        # language can be None, in which case faster-whisper will detect it
        segments, info = self.model.transcribe(str(audio_path), language=self.language, beam_size=5)
        
        print(f"Detected language '{info.language}' with probability {info.language_probability}")
        
        full_text = []
        # Ensure parent directory exists
        output_text_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_text_path, "w", encoding="utf-8") as f:
            for segment in segments:
                text = segment.text
                full_text.append(text)
                # Write standard transcript
                f.write(f"[{segment.start:.2f}s -> {segment.end:.2f}s] {text}\n")
                
        compiled_text = " ".join(full_text)
        print(f"Transcription saved to {output_text_path}")
        return compiled_text
