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
        self.actual_rate = config.RATE
        self.actual_channels = config.CHANNELS

    def start(self):
        if self.is_recording:
            return
            
        self.frames = []
        self.is_recording = True
        
        try:
            default_device_info = self.p.get_default_input_device_info()
            print(f"🎤 Périphérique d'entrée sélectionné: {default_device_info['name']}")
            print(f"   Canaux max: {default_device_info['maxInputChannels']}, Fréquence par défaut: {default_device_info['defaultSampleRate']}Hz")
        except Exception as e:
            print(f"⚠️ Impossible d'obtenir les infos du périphérique d'entrée par défaut: {e}")
            default_device_info = None

        try:
            self.actual_rate = config.RATE
            self.actual_channels = config.CHANNELS
            self.stream = self.p.open(format=self.format,
                                      channels=self.actual_channels,
                                      rate=self.actual_rate,
                                      input=True,
                                      frames_per_buffer=config.CHUNK)
        except Exception as e:
            print(f"⚠️ Erreur avec le taux {config.RATE}Hz ({e}). Tentative avec le taux par défaut du périphérique...")
            if default_device_info:
                try:
                    self.actual_rate = int(default_device_info['defaultSampleRate'])
                    self.actual_channels = int(default_device_info.get('maxInputChannels', 1)) or 1
                    self.stream = self.p.open(format=self.format,
                                              channels=self.actual_channels,
                                              rate=self.actual_rate,
                                              input=True,
                                              frames_per_buffer=config.CHUNK)
                    print(f"✅ Succès avec {self.actual_rate}Hz et {self.actual_channels} canaux.")
                except Exception as e2:
                    print(f"❌ Erreur critique au fallback: Impossible d'ouvrir le flux audio ! {e2}")
                    self.is_recording = False
                    return
            else:
                print(f"❌ Erreur critique: Pas d'infos pour le fallback. {e}")
                self.is_recording = False
                return
                                  
        self.record_thread = threading.Thread(target=self._record_loop)
        self.record_thread.start()
        print("🔴 Enregistrement audio démarré...")

    def _record_loop(self):
        chunks_read = 0
        chunks_per_sec = max(1, int(self.actual_rate / config.CHUNK))
        
        while self.is_recording:
            try:
                data = self.stream.read(config.CHUNK, exception_on_overflow=False)
                self.frames.append(data)
                chunks_read += 1
                
                # Check volume every ~1 second to ensure we capture sound
                if chunks_read % chunks_per_sec == 0:
                    try:
                        import audioop
                        sample_width = self.p.get_sample_size(self.format)
                        rms = audioop.rms(data, sample_width)
                        
                        if rms > 200:
                            print(f"[Audio] 🎤 {chunks_read // chunks_per_sec}s - Son détecté (Volume RMS: {rms})", end='\r')
                        else:
                            print(f"[Audio] ⚠️ {chunks_read // chunks_per_sec}s - Silence ou très faible volume (RMS: {rms})", end='\r')
                    except ImportError:
                        print(f"[Audio] 🎤 {chunks_read // chunks_per_sec}s - Enregistrement en cours...", end='\r')
                        
            except Exception as e:
                print(f"\n❌ Erreur de lecture du stream audio: {e}")
                break
        print("\n⏹️  Fin de la boucle d'enregistrement.")

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
        wf.setnchannels(self.actual_channels)
        wf.setsampwidth(self.p.get_sample_size(self.format))
        wf.setframerate(self.actual_rate)
        wf.writeframes(b''.join(self.frames))
        wf.close()
        
        print(f"Recording saved to {output_path}")

    def cleanup(self):
        self.p.terminate()
