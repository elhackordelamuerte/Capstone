import threading
from pathlib import Path
from transcriber import Transcriber
from summarizer import Summarizer

class Pipeline:
    def __init__(self):
        self.transcriber = Transcriber()
        self.summarizer = Summarizer()
        self.status = "idle"
        self.progress = 0

    def process_meeting(self, audio_path: Path, output_dir: Path, language: str, callback=None):
        def _run():
            try:
                self.status = "transcribing"
                self.progress = 10
                if callback: callback(self.status, self.progress)
                
                txt_path = output_dir / "transcription.txt"
                self.transcriber.language = language
                transcription = self.transcriber.transcribe(audio_path, txt_path)
                
                self.status = "summarizing"
                self.progress = 60
                if callback: callback(self.status, self.progress)
                
                md_path = output_dir / "compte_rendu.md"
                success = self.summarizer.generate_summary(transcription, md_path, language)
                
                if success:
                    self.status = "done"
                    self.progress = 100
                else:
                    self.status = "error_summarizing"
                    
                if callback: callback(self.status, self.progress)
                    
            except Exception as e:
                print(f"Pipeline error: {e}")
                self.status = f"error: {str(e)}"
                if callback: callback(self.status, 0)
                
        thread = threading.Thread(target=_run)
        thread.start()
