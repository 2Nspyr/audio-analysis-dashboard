"""Pitch tracking + tuning reference detection.

Method: frame-based autocorrelation (ACF) pitch detection, vectorized with
numpy FFTs and processed in batches to bound memory on long files. This is
a standard, dependency-free (no librosa) approach to fundamental frequency
estimation, similar in spirit to the classic autocorrelation method used in
tools like Praat.
"""
import numpy as np

MIN_F0 = 60.0     # Hz - lower bound of pitch search range
MAX_F0 = 1000.0   # Hz - upper bound of pitch search range
FRAME_LEN = 4096
HOP = 2048
VOICING_THRESHOLD = 0.35  # normalized ACF peak strength required to call a frame "pitched"
BATCH_FRAMES = 4000

REFERENCE_PITCHES = [432.0, 434.0, 436.0, 438.0, 440.0, 442.0, 444.0, 446.0, 448.0]
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def _frame_signal(x, frame_len, hop):
    n_frames = 1 + (len(x) - frame_len) // hop
    if n_frames <= 0:
        return np.empty((0, frame_len), dtype=np.float32)
    shape = (n_frames, frame_len)
    strides = (x.strides[0] * hop, x.strides[0])
    return np.lib.stride_tricks.as_strided(x, shape=shape, strides=strides)


def track_pitch(mono: np.ndarray, sr: int):
    """Returns list of dicts: {time_sec, freq_hz, strength} for frames judged
    to have clear tonal/periodic content. Empty list if signal too short."""
    if len(mono) < FRAME_LEN:
        return []

    frames = _frame_signal(mono, FRAME_LEN, HOP)
    n_frames = frames.shape[0]
    window = np.hanning(FRAME_LEN).astype(np.float32)

    min_lag = int(sr / MAX_F0)
    max_lag = int(sr / MIN_F0)
    max_lag = min(max_lag, FRAME_LEN - 1)

    results = []
    fft_size = 1
    while fft_size < 2 * FRAME_LEN:
        fft_size *= 2

    for start in range(0, n_frames, BATCH_FRAMES):
        batch = frames[start:start + BATCH_FRAMES]
        # skip near-silent frames
        rms = np.sqrt(np.mean(batch.astype(np.float64) ** 2, axis=1))
        active = rms > (rms.max() * 0.02 + 1e-9) if rms.max() > 0 else np.zeros(len(rms), dtype=bool)

        windowed = batch * window
        spec = np.fft.rfft(windowed, n=fft_size, axis=1)
        power = spec.real ** 2 + spec.imag ** 2
        acf = np.fft.irfft(power, n=fft_size, axis=1)[:, :FRAME_LEN]
        acf0 = acf[:, 0:1]
        acf0_safe = np.where(acf0 == 0, 1.0, acf0)
        acf_norm = acf / acf0_safe

        search = acf_norm[:, min_lag:max_lag + 1]
        best_lag_rel = np.argmax(search, axis=1)
        best_lag = best_lag_rel + min_lag
        best_strength = search[np.arange(len(search)), best_lag_rel]

        for i in range(len(batch)):
            if not active[i]:
                continue
            if best_strength[i] < VOICING_THRESHOLD:
                continue
            lag = int(best_lag[i])
            if lag <= 0:
                continue

            # Integer-sample lag alone quantizes frequency in coarse steps
            # (e.g. ~6 Hz apart near 500 Hz at 44.1 kHz) - too coarse for a
            # 15-cent tuning tolerance. Parabolic interpolation around the
            # ACF peak recovers sub-sample precision cheaply and standard
            # in autocorrelation pitch trackers.
            refined_lag = float(lag)
            if 0 < lag < FRAME_LEN - 1:
                y0, y1, y2 = acf_norm[i, lag - 1], acf_norm[i, lag], acf_norm[i, lag + 1]
                denom = (y0 - 2 * y1 + y2)
                if denom != 0:
                    offset = 0.5 * (y0 - y2) / denom
                    if -1.0 < offset < 1.0:
                        refined_lag = lag + offset

            freq = sr / refined_lag
            t = (start + i) * HOP / sr
            results.append({
                "time_sec": t,
                "freq_hz": float(freq),
                "strength": float(best_strength[i]),
            })

    return results


def _cents_off_from_grid(freq_hz, ref_a4):
    """Nearest equal-temperament note (12-TET) built on ref_a4, and cents deviation."""
    if freq_hz <= 0:
        return None
    midi_float = 69 + 12 * np.log2(freq_hz / ref_a4)
    nearest_midi = round(midi_float)
    cents = (midi_float - nearest_midi) * 100.0
    note_name = NOTE_NAMES[int(nearest_midi) % 12]
    octave = int(nearest_midi) // 12 - 1
    return cents, f"{note_name}{octave}"


def analyze_tuning(mono: np.ndarray, sr: int, duration_sec: float):
    pitches = track_pitch(mono, sr)

    if len(pitches) < 20:
        return {
            "has_pitched_content": False,
            "message": "No clear pitched content detected — this track reads as ambient/drone, "
                       "spoken word, or noise-based content rather than having a stable musical "
                       "fundamental frequency to compare against a tuning grid.",
            "best_reference": None,
            "confidence_pct": None,
            "drift_detected": False,
            "num_pitched_frames": len(pitches),
            "pitch_series": pitches,
        }

    CENTS_TOLERANCE = 15.0
    freqs = np.array([p["freq_hz"] for p in pitches])

    scores = {}
    mean_abs_cents = {}
    for ref in REFERENCE_PITCHES:
        cents_devs = []
        for f in freqs:
            cents, _ = _cents_off_from_grid(f, ref)
            cents_devs.append(cents)
        cents_devs = np.array(cents_devs)
        in_tolerance = np.abs(cents_devs) <= CENTS_TOLERANCE
        scores[ref] = float(np.mean(in_tolerance) * 100.0)
        mean_abs_cents[ref] = float(np.mean(np.abs(cents_devs)))

    # Pick the reference with the highest in-tolerance %; break ties (common
    # for a single sustained pitch, which can sit within tolerance of several
    # adjacent reference grids at once) by which grid it sits CLOSEST to on
    # average, not just whichever happened to be checked first.
    best_reference = max(REFERENCE_PITCHES, key=lambda r: (scores[r], -mean_abs_cents[r]))
    confidence = scores[best_reference]

    # Drift check: split track into thirds by time, compare mean cents deviation
    # (relative to the best reference) across segments.
    times = np.array([p["time_sec"] for p in pitches])
    cents_at_best = np.array([_cents_off_from_grid(f, best_reference)[0] for f in freqs])

    drift_detected = False
    drift_detail = None
    if duration_sec > 60 and len(pitches) > 30:
        thirds_edges = [0, duration_sec / 3, 2 * duration_sec / 3, duration_sec]
        seg_means = []
        for i in range(3):
            mask = (times >= thirds_edges[i]) & (times < thirds_edges[i + 1])
            if mask.sum() > 5:
                seg_means.append(float(np.mean(cents_at_best[mask])))
            else:
                seg_means.append(None)
        valid = [m for m in seg_means if m is not None]
        if len(valid) >= 2:
            spread = max(valid) - min(valid)
            if spread > 12.0:
                drift_detected = True
            drift_detail = {"segment_means_cents": seg_means, "spread_cents": spread}

    return {
        "has_pitched_content": True,
        "message": None,
        "best_reference": best_reference,
        "confidence_pct": round(confidence, 1),
        "all_scores": {str(k): round(v, 1) for k, v in scores.items()},
        "drift_detected": drift_detected,
        "drift_detail": drift_detail,
        "num_pitched_frames": len(pitches),
        "total_frames_considered": int(len(mono) / HOP),
        "pitch_series": pitches[::max(1, len(pitches) // 500)],  # downsample for report/plot
    }
