"""Harmonic balance: energy distribution across frequency bands."""
import numpy as np
from scipy.signal import welch
from scipy.signal.windows import hann

BANDS = [
    ("sub-bass", 20, 60),
    ("bass", 60, 250),
    ("low-mid", 250, 500),
    ("mid", 500, 2000),
    ("high-mid", 2000, 4000),
    ("high", 4000, 20000),
]

# welch()'s memory cost scales with how many segments it has to process,
# which scales with the array's full length. This stage runs on the
# highest-resolution audio in the whole pipeline (bands go up to 20kHz, so
# there's no downsampling it away like the other stages), so a 25-40 minute
# track (this app's real use case) was measured as the single biggest
# memory spike anywhere in the pipeline: +900MB in profiling on a
# 25-minute file. Overall energy balance across bands is a stationary
# characteristic of a track's mix, not something that needs every second to
# measure accurately, so sampling a bounded, spread-out subset (start,
# middle, end) instead of the entire track keeps this stage's memory flat
# regardless of duration while still covering how the mix might shift over
# a long session.
MAX_SAMPLE_SEC = 90
N_SAMPLE_WINDOWS = 3


def _representative_sample(mono: np.ndarray, sr: int) -> np.ndarray:
    window_len = int(MAX_SAMPLE_SEC * sr)
    if len(mono) <= window_len * N_SAMPLE_WINDOWS:
        return mono

    starts = np.linspace(0, len(mono) - window_len, N_SAMPLE_WINDOWS).astype(int)
    return np.concatenate([mono[s:s + window_len] for s in starts])


def analyze_harmonic_balance(mono: np.ndarray, sr: int):
    sample = _representative_sample(mono, sr)
    nperseg = min(len(sample), 65536)
    if nperseg < 1024:
        return {"bands": [], "message": "Track too short to analyze."}

    # Explicit float32 window: scipy's default window construction is
    # float64, and welch's internal segmented-FFT array silently upcasts to
    # match it, roughly doubling this stage's working memory for no benefit
    # at audio bit depths (same fix applied in spectrogram.py/binaural.py).
    window = hann(nperseg, sym=False).astype(np.float32)
    f, pxx = welch(sample, fs=sr, window=window, nperseg=nperseg)

    total_energy = 0.0
    band_energies = []
    for name, lo, hi in BANDS:
        mask = (f >= lo) & (f < hi)
        energy = float(np.sum(pxx[mask]))
        band_energies.append([name, lo, hi, energy])
        total_energy += energy

    bands = []
    for name, lo, hi, energy in band_energies:
        pct = (energy / total_energy * 100.0) if total_energy > 0 else 0.0
        bands.append({"name": name, "range": f"{lo}-{hi} Hz", "pct": round(pct, 1)})

    # simple qualitative read
    low_pct = sum(b["pct"] for b in bands if b["name"] in ("sub-bass", "bass"))
    high_pct = sum(b["pct"] for b in bands if b["name"] in ("high-mid", "high"))
    if low_pct > 55:
        character = "bass-heavy"
    elif high_pct > 45:
        character = "bright/thin"
    else:
        character = "balanced"

    return {
        "bands": bands,
        "character": character,
    }
