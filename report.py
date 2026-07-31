"""Builds the full analysis report for a loaded audio file and a
plain-language summary paragraph."""
import os
import time

from analysis.pitch import analyze_tuning
from analysis.spectrogram import generate_spectrogram_image
from analysis.binaural import analyze_binaural
from analysis.isochronic import analyze_isochronic
from analysis.harmonic import analyze_harmonic_balance


def build_report(audio, filename, reports_dir, report_id, progress_cb=None):
    """progress_cb, if given, is called with a short stage name before each
    analysis step starts - lets the caller surface progress to the user."""
    def stage(name):
        if progress_cb:
            progress_cb(name)

    sr = audio["sr"]
    mono = audio["mono"]
    data = audio["data"]
    channels = audio["channels"]
    duration_sec = audio["duration_sec"]

    stage("tuning reference")
    tuning = analyze_tuning(mono, sr, duration_sec)

    stage("spectrogram")
    spec_filename = f"{report_id}_spectrogram.png"
    spec_path = os.path.join(reports_dir, spec_filename)
    generate_spectrogram_image(mono, sr, spec_path)

    stage("binaural beat")
    binaural = analyze_binaural(data, sr, channels)

    stage("isochronic pulse")
    isochronic = analyze_isochronic(mono, sr)

    stage("harmonic balance")
    harmonic = analyze_harmonic_balance(mono, sr)

    summary = _build_summary(tuning, binaural, isochronic, harmonic)

    minutes = int(duration_sec // 60)
    seconds = int(duration_sec % 60)

    return {
        "filename": filename,
        "duration": f"{minutes}:{seconds:02d}",
        "duration_sec": round(duration_sec, 1),
        "sample_rate": sr,
        "channels": "Stereo" if channels == 2 else ("Mono" if channels == 1 else f"{channels}-channel"),
        "tuning": tuning,
        "spectrogram_image": spec_filename,
        "binaural": binaural,
        "isochronic": isochronic,
        "harmonic": harmonic,
        "summary": summary,
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }


def _build_summary(tuning, binaural, isochronic, harmonic):
    parts = []

    if tuning["has_pitched_content"]:
        ref = tuning["best_reference"]
        conf = tuning["confidence_pct"]
        drift = " Tuning drifts noticeably over the course of the track." if tuning["drift_detected"] else ""
        parts.append(f"This track is tuned closest to A={ref:.0f} Hz ({conf:.0f}% confidence).{drift}")
    else:
        parts.append("This track has no clear pitched content to assign a tuning reference to.")

    if binaural.get("applicable") and binaural.get("detected"):
        steadiness = "steady" if binaural.get("steady") else "variable"
        parts.append(f"It holds a {steadiness} {binaural['beat_hz']:.1f} Hz binaural beat ({binaural['band']} range) throughout.")
    elif binaural.get("applicable"):
        parts.append("No binaural beat was detected.")

    if isochronic.get("detected"):
        parts.append(f"An isochronic pulse at {isochronic['rate_hz']:.1f} Hz is present ({'steady' if isochronic['steady'] else 'variable'}).")
    else:
        parts.append("No isochronic pulsing was detected.")

    if harmonic.get("bands"):
        parts.append(f"The frequency profile reads as {harmonic['character']}.")

    return " ".join(parts)
