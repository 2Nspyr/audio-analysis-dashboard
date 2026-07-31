"""Binaural beat detection: compares dominant frequency content of the left
vs right channel. A true binaural beat is two near-pure tones, one per ear,
offset by a small Hz difference — so we look for a consistent dominant-peak
offset between channels across time, not just a single global comparison.
"""
import numpy as np
from scipy.signal import welch
from analysis.dsp_utils import cascade_decimate

BAND_LABELS = [
    (0.5, 4, "delta"),
    (4, 8, "theta"),
    (8, 13, "alpha"),
    (13, 30, "beta"),
    (30, 100, "gamma"),
]

MIN_CARRIER_HZ = 40
MAX_CARRIER_HZ = 2000
MAX_BEAT_HZ = 40  # beats above this aren't perceptible/typical for binaural entrainment
N_SEGMENTS = 6


def _band_label(beat_hz):
    for lo, hi, name in BAND_LABELS:
        if lo <= beat_hz < hi:
            return name
    return "sub-delta" if beat_hz < 0.5 else "above-gamma"


def _dominant_peak(x, sr, fmin=MIN_CARRIER_HZ, fmax=MAX_CARRIER_HZ):
    nperseg = min(len(x), 65536)
    if nperseg < 1024:
        return None, None
    f, pxx = welch(x, fs=sr, nperseg=nperseg)
    mask = (f >= fmin) & (f <= fmax)
    if not mask.any():
        return None, None
    f_sub = f[mask]
    pxx_sub = pxx[mask]
    idx = np.argmax(pxx_sub)
    peak_freq = f_sub[idx]
    peak_power = pxx_sub[idx]
    median_power = np.median(pxx_sub)
    prominence = peak_power / (median_power + 1e-12)
    return float(peak_freq), float(prominence)


def analyze_binaural(data: np.ndarray, sr: int, channels: int):
    if channels != 2:
        return {
            "applicable": False,
            "detected": False,
            "message": "Not applicable — file is mono, so there are no separate left/right "
                       "channels to compare.",
        }

    # Carrier tones of interest top out at MAX_CARRIER_HZ (2000 Hz), so working
    # at full sample rate (commonly 44.1/48kHz) wastes memory holding two
    # full-resolution channel copies for a stage that only needs ~5x that
    # bandwidth. Downsampling first cuts the array size (and everything
    # derived from it) by roughly sr/5000x with no loss of relevant signal.
    left, ds_sr = cascade_decimate(data[:, 0], sr, MAX_CARRIER_HZ * 2.5)
    right, _ = cascade_decimate(data[:, 1], sr, MAX_CARRIER_HZ * 2.5)
    sr = ds_sr

    peak_l, prom_l = _dominant_peak(left, sr)
    peak_r, prom_r = _dominant_peak(right, sr)

    MIN_PROMINENCE = 4.0

    if peak_l is None or peak_r is None or prom_l < MIN_PROMINENCE or prom_r < MIN_PROMINENCE:
        return {
            "applicable": True,
            "detected": False,
            "message": "No binaural beat detected — neither channel shows a clear, dominant "
                       "tone to compare.",
            "left_peak_hz": peak_l,
            "right_peak_hz": peak_r,
        }

    global_beat = abs(peak_l - peak_r)

    # Consistency check across time segments
    n = len(left)
    seg_len = n // N_SEGMENTS
    seg_beats = []
    if seg_len > sr * 2:  # need at least ~2s per segment
        for i in range(N_SEGMENTS):
            s, e = i * seg_len, (i + 1) * seg_len
            pl, prl = _dominant_peak(left[s:e], sr)
            pr, prr = _dominant_peak(right[s:e], sr)
            if pl is not None and pr is not None and prl >= MIN_PROMINENCE and prr >= MIN_PROMINENCE:
                seg_beats.append(abs(pl - pr))

    if seg_beats:
        seg_beats_arr = np.array(seg_beats)
        beat_std = float(np.std(seg_beats_arr))
        beat_mean = float(np.mean(seg_beats_arr))
    else:
        beat_std = None
        beat_mean = global_beat

    if beat_mean > MAX_BEAT_HZ or beat_mean < 0.1:
        return {
            "applicable": True,
            "detected": False,
            "message": f"No binaural beat detected — channels differ by ~{global_beat:.1f} Hz, "
                       f"outside the range typical for binaural entrainment (channel peaks are "
                       f"likely just different musical content, not an intentional beat).",
            "left_peak_hz": round(peak_l, 2),
            "right_peak_hz": round(peak_r, 2),
        }

    consistent = beat_std is None or beat_std < max(1.0, beat_mean * 0.25)

    if not consistent:
        return {
            "applicable": True,
            "detected": False,
            "message": "No consistent binaural beat detected — the left/right frequency offset "
                       "varies too much across the track to call it an intentional binaural beat.",
            "left_peak_hz": round(peak_l, 2),
            "right_peak_hz": round(peak_r, 2),
            "segment_beats_hz": [round(b, 2) for b in seg_beats],
        }

    band = _band_label(beat_mean)
    return {
        "applicable": True,
        "detected": True,
        "beat_hz": round(beat_mean, 2),
        "band": band,
        "left_peak_hz": round(peak_l, 2),
        "right_peak_hz": round(peak_r, 2),
        "steady": beat_std is not None and beat_std < max(0.5, beat_mean * 0.1),
        "segment_beats_hz": [round(b, 2) for b in seg_beats] if seg_beats else None,
        "message": f"Binaural beat detected: {beat_mean:.1f} Hz ({band} range).",
    }
