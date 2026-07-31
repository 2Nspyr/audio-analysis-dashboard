import os
import uuid
import threading
import traceback

from flask import Flask, request, render_template, redirect, url_for, flash, jsonify

from audio_io import load_audio, AudioLoadError
from report import build_report
from youtube_dl import is_youtube_url, download_audio, YouTubeDownloadError
from generation import (
    generate_pure_tone, generate_binaural, generate_isochronic,
    layer_with_import, write_wav,
)
from analysis.binaural import analyze_binaural
from analysis.isochronic import analyze_isochronic
import jobs

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "static", "uploads")
REPORTS_DIR = os.path.join(BASE_DIR, "static", "reports")
WORK_DIR = os.path.join(BASE_DIR, "static", "work")
GENERATED_DIR = os.path.join(BASE_DIR, "static", "generated")

for d in (UPLOAD_DIR, REPORTS_DIR, WORK_DIR, GENERATED_DIR):
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


def _run_file_analysis(job_id, upload_path, filename, report_id):
    try:
        jobs.set_stage(job_id, "loading audio")
        audio = load_audio(upload_path, WORK_DIR)
        report = build_report(
            audio, filename, REPORTS_DIR, report_id,
            progress_cb=lambda stage: jobs.set_stage(job_id, stage),
        )
        reports_cache[report_id] = report
        jobs.set_done(job_id, f"/report/{report_id}")
    except AudioLoadError as e:
        jobs.set_error(job_id, f"Could not read this audio file: {e}")
    except Exception as e:
        traceback.print_exc()
        jobs.set_error(job_id, f"Analysis failed: {e}")


def _run_url_analysis(job_id, url, report_id):
    try:
        jobs.set_stage(job_id, "downloading from YouTube")
        downloaded_wav = download_audio(url, WORK_DIR)
        jobs.set_stage(job_id, "loading audio")
        audio = load_audio(downloaded_wav, WORK_DIR)
        report = build_report(
            audio, url, REPORTS_DIR, report_id,
            progress_cb=lambda stage: jobs.set_stage(job_id, stage),
        )
        reports_cache[report_id] = report
        jobs.set_done(job_id, f"/report/{report_id}")
    except YouTubeDownloadError as e:
        jobs.set_error(job_id, f"Could not download that video's audio: {e}")
    except AudioLoadError as e:
        jobs.set_error(job_id, f"Could not read the downloaded audio: {e}")
    except Exception as e:
        traceback.print_exc()
        jobs.set_error(job_id, f"Analysis failed: {e}")


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

    job_id = jobs.create_job("analyze")
    threading.Thread(
        target=_run_file_analysis, args=(job_id, upload_path, file.filename, report_id), daemon=True
    ).start()
    return redirect(url_for("show_processing", job_id=job_id))


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
    job_id = jobs.create_job("analyze_url")
    threading.Thread(
        target=_run_url_analysis, args=(job_id, url, report_id), daemon=True
    ).start()
    return redirect(url_for("show_processing", job_id=job_id))


@app.route("/processing/<job_id>", methods=["GET"])
def show_processing(job_id):
    job = jobs.get_job(job_id)
    if not job:
        flash("That job could not be found (it may have expired).")
        return redirect(url_for("index"))
    if job["status"] == "done":
        return redirect(job["redirect_url"])
    return render_template("processing.html", job_id=job_id, stages=jobs.STAGES)


@app.route("/job/<job_id>/status", methods=["GET"])
def job_status(job_id):
    job = jobs.get_job(job_id)
    if not job:
        return jsonify({"status": "error", "error": "Job not found"}), 404
    return jsonify(job)


@app.route("/generate", methods=["GET"])
def generate_form():
    return render_template("generate.html")


@app.route("/generate", methods=["POST"])
def generate():
    mode = request.form.get("mode")
    try:
        duration = float(request.form.get("duration", 30))
        duration = max(1, min(duration, 3600))
    except (TypeError, ValueError):
        flash("Invalid duration.")
        return redirect(url_for("generate_form"))

    try:
        if mode == "pure":
            freq = float(request.form.get("freq", 528))
            signal, sr = generate_pure_tone(freq, duration)
            gen_label = f"Pure tone: {freq:.1f} Hz"
            verify = None

        elif mode == "binaural":
            carrier = float(request.form.get("carrier", 200))
            beat = float(request.form.get("beat", 6))
            signal, sr = generate_binaural(carrier, beat, duration)
            gen_label = f"Binaural beat: {carrier:.1f} Hz carrier, {beat:.1f} Hz beat"
            verify = ("binaural", beat)

        elif mode == "isochronic":
            tone_freq = float(request.form.get("tone_freq", 300))
            pulse_rate = float(request.form.get("pulse_rate", 6))
            signal, sr = generate_isochronic(tone_freq, pulse_rate, duration)
            gen_label = f"Isochronic pulse: {tone_freq:.1f} Hz tone, {pulse_rate:.1f} Hz pulse"
            verify = ("isochronic", pulse_rate)

        else:
            flash("Choose a generation mode.")
            return redirect(url_for("generate_form"))
    except (TypeError, ValueError):
        flash("Invalid frequency/duration values.")
        return redirect(url_for("generate_form"))

    # Optional layering under an imported file (e.g. a voice recording)
    layer_file = request.files.get("layer_file")
    if layer_file and layer_file.filename:
        try:
            mix_ratio = float(request.form.get("mix_ratio", 0.4))
            mix_ratio = max(0.0, min(mix_ratio, 1.0))
            gen_id = uuid.uuid4().hex[:8]
            layer_upload_path = os.path.join(UPLOAD_DIR, f"{gen_id}_{layer_file.filename}")
            layer_file.save(layer_upload_path)
            imported_audio = load_audio(layer_upload_path, WORK_DIR)
            signal = layer_with_import(signal, sr, imported_audio["data"], imported_audio["sr"], mix_ratio)
            gen_label += f" (layered under '{layer_file.filename}' at {int(mix_ratio*100)}% bed volume)"
        except Exception as e:
            traceback.print_exc()
            flash(f"Layering failed, generated the bed alone instead: {e}")

    gen_id = uuid.uuid4().hex[:12]
    out_filename = f"{gen_id}.wav"
    out_path = os.path.join(GENERATED_DIR, out_filename)
    write_wav(signal, sr, out_path)

    verification = None
    if verify:
        kind, expected_value = verify
        try:
            audio = load_audio(out_path, WORK_DIR)
            if kind == "binaural":
                result = analyze_binaural(audio["data"], audio["sr"], audio["channels"])
                verification = {
                    "kind": "binaural",
                    "expected": f"{expected_value:.1f} Hz",
                    "detected": result.get("detected"),
                    "detected_value": f"{result.get('beat_hz')} Hz ({result.get('band')})" if result.get("detected") else result.get("message"),
                }
            elif kind == "isochronic":
                result = analyze_isochronic(audio["mono"], audio["sr"])
                verification = {
                    "kind": "isochronic",
                    "expected": f"{expected_value:.1f} Hz",
                    "detected": result.get("detected"),
                    "detected_value": f"{result.get('rate_hz')} Hz" if result.get("detected") else result.get("message"),
                }
        except Exception as e:
            traceback.print_exc()
            verification = {"kind": kind, "error": str(e)}

    return render_template(
        "generate_result.html",
        label=gen_label,
        download_url=url_for("static", filename=f"generated/{out_filename}"),
        verification=verification,
    )


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
