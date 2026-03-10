import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()
MEETINGS_DIR = BASE_DIR / "meetings"
MODELS_DIR = BASE_DIR / "models"

# Audio Settings
AUDIO_FORMAT = "int16" # pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 1024

# STT Settings
# whisper-base is recommended for RPi4
WHISPER_MODEL = "base" 
COMPUTE_TYPE = "int8" # For faster-whisper on CPU

# LLM Settings
# Qwen2.5-1.5B (4GB RAM)
LLM_MODEL_NAME = "Qwen2.5-1.5B-Instruct-Q4_K_M.gguf"
LLM_MODEL_PATH = MODELS_DIR / LLM_MODEL_NAME
N_CTX = 4096 # Context window
N_THREADS = 4 # Adjust based on RPi 4 cores (usually 4)
