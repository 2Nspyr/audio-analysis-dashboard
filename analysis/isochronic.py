"""Isochronic pulse detection: looks at the amplitude envelope (not pitch)
for a repeating on/off rate. Downsamples aggressively first since pulse
rates of interest are low (0.5-40 Hz), which keeps this fast even on long
files and avoids a full-resolution Hilbert transform.
"""
import numpy as np
from scipy.signal import decimate, welch, butter, filtfilt

ENV_SR = 1000  # approximate working sample rate for envelope analysis
MIN_PULSE_HZ = 0.5
MAX_PULSE_HZ = 40
MIN_PROMINENCE = 5.0
N_SEGMENTS = 6


def _downsample(mono, sr, target_sr=ENV_SR):
    """Decimate in cascaded stages (factor <=10 per stage, scipy's recommended
    limit for stable IIR anti-aliasing) so the actual output sample rate is
    always known exactly - avoids the rate-mismatch bugs a single big
    resample_poly ratio approximation can introduce."""
    x = mono.astype(np.float64)
    cur_sr = float(sr)
    while cur_sr / target_sr > 10:
        x = decimate(x, 10, zero_phase=True)
        cur_sr /= 10
    remaining_factor = int(round(cur_sr / target_sr))
    if remaining_factor > 1:
        x = decimate(x, remaining_factor, zero_phase=True)
        cur_sr /= remaining_factor
    return x, cur_sr


def _pulse_rate(env, sr):
    env = env - np.mean(env)
    nperseg = min(len(env), 8192)
    if nperseg < 256:
        return None, None
    f, pxx = welch(env, fs=sr, nperseg=nperseg)
    mask = (f >= MIN_PULSE_HZ) & (f <= MAX_PULSE_HZ)
    if not mask.any():
        return None, None
    f_sub = f[mask]
    pxx_sub = pxx[mask]
    idx = np.argmax(pxx_sub)

    # Real periodic gating shows up as a genuine local maximum in the
    # spectrum. Natural loudness dynamics (song swells, phrasing, breath)
    # instead produce a spectrum that just decays monotonically toward 0 Hz,
    # so its "peak" always lands right at the edge of our search band - that's
    # not a real periodicity, it's an edge artifact of where we started
    # looking. Reject peaks sitting at either edge of the search range.
    if idx == 0 or idx == len(f_sub) - 1:
        return None, None

    peak_freq = f_sub[idx]
    peak_power = pxx_sub[idx]
    median_power = np.median(pxx_sub)
    prominence = peak_power / (median_power + 1e-12)
    return float(peak_freq), float(prominence)


def analyze_isochronic(mono: np.ndarray, sr: int):
    ds, env_sr = _downsample(mono, sr)
    raw_envelope = np.abs(ds)
    dc_level = float(np.mean(raw_envelope)) + 1e-12

    # Rectification (abs) creates strong energy at 2x the original signal's
    # frequency content, which can alias into the low-frequency band we care
    # about once sampled at env_sr. A hard low-pass right above the pulse
    # search range removes that artifact and leaves only genuine slow
    # amplitude modulation (real on/off gating).
    cutoff = MAX_PULSE_HZ * 1.25
    nyq = env_sr / 2.0
    envelope = raw_envelope
    if cutoff < nyq:
        b, a = butter(4, cutoff / nyq, btype="low")
        envelope = filtfilt(b, a, raw_envelope)

    envelope = envelope - np.mean(envelope)

    # Modulation depth: real on/off gating swings the envelope by a large
    # fraction of its average level. Filter artifacts / numerical noise from
    # an essentially flat envelope produce a spectral "peak" too (since the
    # true low-frequency floor is near zero), but its absolute size relative
    # to the signal's actual loudness is tiny - this check filters that out.
    modulation_depth = float(np.std(envelope)) / dc_level

    peak_freq, prominence = _pulse_rate(envelope, env_sr)

    MIN_MODULATION_DEPTH = 0.12

    if peak_freq is None or prominence < MIN_PROMINENCE or modulation_depth < MIN_MODULATION_DEPTH:
        return {
            "detected": False,
            "message": "None detected — no repeating on/off amplitude pattern found in the "
                       "0.5–40 Hz range.",
        }

    # steadiness check across segments
    n = len(envelope)
    seg_len = n // N_SEGMENTS
    seg_rates = []
    if seg_len > env_sr * 3:
        for i in range(N_SEGMENTS):
            s, e = i * seg_len, (i + 1) * seg_len
            pf, prom = _pulse_rate(envelope[s:e], env_sr)
            if pf is not None and prom >= MIN_PROMINENCE * 0.6:
                seg_rates.append(pf)

    steady = True
    if len(seg_rates) >= 3:
        spread = max(seg_rates) - min(seg_rates)
        steady = spread < max(0.3, peak_freq * 0.15)

    message = f"Isochronic pulse detected: {peak_freq:.1f} Hz ({'steady' if steady else 'variable'} across the track)."
    caveat = None
    if not steady and peak_freq < 6.0:
        caveat = ("Note: an unsteady rate in this low range can also come from natural speech/vocal "
                  "rhythm rather than a deliberately programmed pulse — worth a listen to confirm.")

    return {
        "detected": True,
        "rate_hz": round(peak_freq, 2),
        "steady": steady,
        "segment_rates_hz": [round(r, 2) for r in seg_rates] if seg_rates else None,
        "caveat": caveat,
        "message": message,
    }
