"""Harmonic balance: energy distribution across frequency bands."""
import numpy as np
from scipy.signal import welch

BANDS = [
    ("sub-bass", 20, 60),
    ("bass", 60, 250),
    ("low-mid", 250, 500),
    ("mid", 500, 2000),
    ("high-mid", 2000, 4000),
    ("high", 4000, 20000),
]


def analyze_harmonic_balance(mono: np.ndarray, sr: int):
    nperseg = min(len(mono), 65536)
    if nperseg < 1024:
        return {"bands": [], "message": "Track too short to analyze."}

    f, pxx = welch(mono, fs=sr, nperseg=nperseg)

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
