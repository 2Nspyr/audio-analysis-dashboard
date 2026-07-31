import os
import uuid
import traceback

from flask import Flask, request, render_template, redirect, url_for, flash

from audio_io import load_audio, AudioLoadError
from report import build_report
from youtube_dl import is_youtube_url, download_audio, YouTubeDownloadError

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "static", "uploads")
REPORTS_DIR = os.path.join(BASE_DIR, "static", "reports")
WORK_DIR = os.path.join(BASE_DIR, "static", "work")

for d in (UPLOAD_DIR, REPORTS_DIR, WORK_DIR):
    os.makedirs(d, exist_ok=True)

ALLOWED_EXT = {"wav", "mp3", "m4a", "aac", "flac", "ogg"}

app = Flask(__name__)
app.secret_key = "dev-secret-key-change-if-shared"
app.config["MAX_CONTENT_LENGTH"] = 300 * 1024 * 1024  # 300MB

reports_cache = {}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    file = request.files.get("audio_file")
    if not file or file.filename == "":
        flash("Please choose an audio file.")
        return redirect(url_for("index"))

    if not allowed_file(file.filename):
        flash(f"Unsupported file type. Allowed: {', '.join(sorted(ALLOWED_EXT))}")
        return redirect(url_for("index"))

    report_id = uuid.uuid4().hex[:12]
    safe_name = f"{report_id}_{file.filename}"
    upload_path = os.path.join(UPLOAD_DIR, safe_name)
    file.save(upload_path)

    try:
        audio = load_audio(upload_path, WORK_DIR)
        report = build_report(audio, file.filename, REPORTS_DIR, report_id)
    except AudioLoadError as e:
        flash(f"Could not read this audio file: {e}")
        return redirect(url_for("index"))
    except Exception as e:
        traceback.print_exc()
        flash(f"Analysis failed: {e}")
        return redirect(url_for("index"))

    reports_cache[report_id] = report
    return redirect(url_for("show_report", report_id=report_id))


@app.route("/analyze_url", methods=["POST"])
def analyze_url():
    url = (request.form.get("youtube_url") or "").strip()
    if not url:
        flash("Please paste a YouTube URL.")
        return redirect(url_for("index"))

    if not is_youtube_url(url):
        flash("That doesn't look like a YouTube URL (expected youtube.com/watch?v=... or youtu.be/...).")
        return redirect(url_for("index"))

    report_id = uuid.uuid4().hex[:12]

    try:
        downloaded_wav = download_audio(url, WORK_DIR)
    except YouTubeDownloadError as e:
        flash(f"Could not download that video's audio: {e}")
        return redirect(url_for("index"))

    try:
        audio = load_audio(downloaded_wav, WORK_DIR)
        report = build_report(audio, url, REPORTS_DIR, report_id)
    except AudioLoadError as e:
        flash(f"Could not read the downloaded audio: {e}")
        return redirect(url_for("index"))
    except Exception as e:
        traceback.print_exc()
        flash(f"Analysis failed: {e}")
        return redirect(url_for("index"))

    reports_cache[report_id] = report
    return redirect(url_for("show_report", report_id=report_id))


@app.route("/report/<report_id>", methods=["GET"])
def show_report(report_id):
    report = reports_cache.get(report_id)
    if not report:
        flash("Report not found (it may have expired — this tool doesn't persist reports).")
        return redirect(url_for("index"))
    return render_template("report.html", r=report)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    app.run(host="0.0.0.0", port=port, debug=True)
