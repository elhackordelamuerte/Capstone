import os
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO

import config
from recorder import AudioRecorder
from pipeline import Pipeline

app = Flask(__name__)
app.config['SECRET_KEY'] = 'meeting-recorder-secret'
# Use standard threading async_mode since we use heavy C extensions
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

recorder = AudioRecorder()
pipeline = Pipeline()

current_meeting = None

def broadcast_status(status, progress=None):
    data = {"status": status}
    if progress is not None:
        data["progress"] = progress
    socketio.emit("status_update", data)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/meetings/create", methods=["POST"])
def create_meeting():
    global current_meeting
    data = request.json
    name = data.get("name", "Réunion").replace(" ", "-").lower()
    date_str = data.get("date", datetime.now().strftime("%Y-%m-%d"))
    lang = data.get("language", "fr")
    
    meeting_id = f"{name}_{date_str}"
    folder_path = config.MEETINGS_DIR / meeting_id
    folder_path.mkdir(parents=True, exist_ok=True)
    
    current_meeting = {
        "id": meeting_id,
        "folder": folder_path,
        "language": lang,
        "audio_file": folder_path / "audio.wav"
    }
    
    return jsonify({
        "status": "ok",
        "meeting_id": meeting_id,
        "folder": str(folder_path)
    })

@app.route("/api/recording/start", methods=["POST"])
def start_recording():
    if not current_meeting:
        return jsonify({"error": "No meeting created"}), 400
        
    recorder.start()
    broadcast_status("recording")
    return jsonify({"status": "recording started"})

@app.route("/api/recording/stop", methods=["POST"])
def stop_recording():
    if not current_meeting:
        return jsonify({"error": "No meeting"}), 400
        
    recorder.stop(current_meeting["audio_file"])
    broadcast_status("saving")
    
    # Start pipeline
    pipeline.process_meeting(
        audio_path=current_meeting["audio_file"],
        output_dir=current_meeting["folder"],
        language=current_meeting["language"],
        callback=broadcast_status
    )
    
    return jsonify({"status": "recording stopped, pipeline started"})

@app.route("/api/recording/status", methods=["GET"])
def recording_status():
    if recorder.is_recording:
        return jsonify({"status": "recording"})
    return jsonify({"status": pipeline.status, "progress": pipeline.progress})

@app.route("/api/meetings")
def list_meetings():
    if not config.MEETINGS_DIR.exists():
        return jsonify([])
        
    meetings = []
    for d in config.MEETINGS_DIR.iterdir():
        if d.is_dir():
            has_md = (d / "compte_rendu.md").exists()
            
            meetings.append({
                "id": d.name,
                "has_md": has_md
            })
    # Sort meetings by name reverse so newest are at top probably
    meetings.sort(key=lambda x: x["id"], reverse=True)
    return jsonify(meetings)

@app.route("/api/meetings/<meeting_id>/download/<file_type>")
def download_file(meeting_id, file_type):
    folder = config.MEETINGS_DIR / meeting_id
    filename = ""
    if file_type == "md":
        filename = "compte_rendu.md"
    else:
        return "Invalid file type", 400
        
    if not (folder / filename).exists():
        return "File not found", 404
        
    return send_from_directory(folder, filename, as_attachment=True)

if __name__ == "__main__":
    config.MEETINGS_DIR.mkdir(exist_ok=True)
    config.MODELS_DIR.mkdir(exist_ok=True)
    socketio.run(app, host="0.0.0.0", port=5000, allow_unsafe_werkzeug=True)
