"""Frequency file generation: pure tones, binaural beats, isochronic pulses,
with optional layering under an imported file (e.g. a voice recording).
"""
import numpy as np
from scipy.io import wavfile

DEFAULT_SR = 44100
FADE_MS = 15  # fade in/out to avoid clicks at start/end


def _fade(signal_1d, sr, fade_ms=FADE_MS):
    n = len(signal_1d)
    fade_len = min(int(sr * fade_ms / 1000), n // 2)
    if fade_len <= 0:
        return signal_1d
    window = np.ones(n, dtype=np.float32)
    ramp = np.linspace(0, 1, fade_len, dtype=np.float32)
    window[:fade_len] *= ramp
    window[-fade_len:] *= ramp[::-1]
    return signal_1d * window


def generate_pure_tone(freq_hz: float, duration_sec: float, sr: int = DEFAULT_SR, amplitude: float = 0.5):
    t = np.arange(int(sr * duration_sec)) / sr
    tone = amplitude * np.sin(2 * np.pi * freq_hz * t)
    tone = _fade(tone.astype(np.float32), sr)
    return tone, sr  # mono


def generate_binaural(carrier_hz: float, beat_hz: float, duration_sec: float,
                       sr: int = DEFAULT_SR, amplitude: float = 0.5):
    t = np.arange(int(sr * duration_sec)) / sr
    left = amplitude * np.sin(2 * np.pi * carrier_hz * t)
    right = amplitude * np.sin(2 * np.pi * (carrier_hz + beat_hz) * t)
    left = _fade(left.astype(np.float32), sr)
    right = _fade(right.astype(np.float32), sr)
    stereo = np.stack([left, right], axis=1)
    return stereo, sr  # stereo, shape (n, 2)


def generate_isochronic(tone_hz: float, pulse_hz: float, duration_sec: float,
                         sr: int = DEFAULT_SR, amplitude: float = 0.5, duty: float = 0.5):
    t = np.arange(int(sr * duration_sec)) / sr
    tone = amplitude * np.sin(2 * np.pi * tone_hz * t)
    # smooth gate (raised-ish) instead of a hard square wave, to avoid harsh clicking
    # while still producing a clear, detectable on/off rate.
    phase = (t * pulse_hz) % 1.0
    gate = (phase < duty).astype(np.float32)
    # short smoothing at each on/off edge
    smooth_samples = max(1, int(sr * 0.005))
    if smooth_samples > 1:
        kernel = np.ones(smooth_samples) / smooth_samples
        gate = np.convolve(gate, kernel, mode="same")
    pulsed = (tone * gate).astype(np.float32)
    pulsed = _fade(pulsed, sr)
    return pulsed, sr  # mono


MIN_AUDIBLE_HZ = 20.0
ISOCHRONIC_CARRIER_HZ = 200.0  # audible carrier used to make sub-20Hz rates perceivable


def generate_sequence(frequencies, total_duration_sec: float, sr: int = DEFAULT_SR,
                       amplitude: float = 0.5, per_freq_sec: float = None,
                       segment_fade_ms: float = 80.0):
    """Steps through `frequencies` in order, either dividing total_duration_sec
    evenly across the list once (per_freq_sec=None) or looping the list with
    each step held for per_freq_sec until total_duration_sec is filled.

    Many CAFL entries include frequencies below 20 Hz (e.g. brainwave-range
    values like 4, 8, 10). On the original electrical-stimulation devices
    these were pulse rates delivered to the body, not sounds - a 3 Hz sine
    wave is below the floor of human hearing and would just be silence in an
    audio file, not "the frequency" in any perceptible sense. To make every
    entry actually audible (and consistent with how this app already
    represents rates via isochronic pulsing elsewhere), any frequency below
    MIN_AUDIBLE_HZ is rendered as an isochronic pulse - an audible carrier
    tone gated on/off at that rate - instead of a silent/inaudible pure tone.
    Frequencies at or above MIN_AUDIBLE_HZ render as a straightforward pure
    tone, same as the original protocol intends.
    """
    if not frequencies:
        raise ValueError("frequencies list is empty")

    if per_freq_sec is None:
        per_freq_sec = total_duration_sec / len(frequencies)

    segments = []
    remaining = total_duration_sec
    i = 0
    while remaining > 0.01:
        freq = frequencies[i % len(frequencies)]
        seg_dur = min(per_freq_sec, remaining)

        if freq < MIN_AUDIBLE_HZ:
            seg, _ = generate_isochronic(ISOCHRONIC_CARRIER_HZ, freq, seg_dur, sr=sr, amplitude=amplitude)
        else:
            seg, _ = generate_pure_tone(freq, seg_dur, sr=sr, amplitude=amplitude)

        seg = _fade(seg, sr, fade_ms=segment_fade_ms)
        segments.append(seg)
        remaining -= seg_dur
        i += 1

    full = np.concatenate(segments)
    return full, sr  # mono


def to_stereo(mono_or_stereo):
    if mono_or_stereo.ndim == 1:
        return np.stack([mono_or_stereo, mono_or_stereo], axis=1)
    return mono_or_stereo


def layer_with_import(generated, generated_sr, imported_mono_or_stereo, imported_sr, mix_ratio: float):
    """mix_ratio is the weight of the GENERATED bed, 0..1. The imported audio
    gets (1 - mix_ratio). Imported audio is resampled to generated_sr if needed
    and trimmed/looped to match the generated signal's length."""
    from scipy.signal import resample_poly
    from math import gcd

    imported = imported_mono_or_stereo
    if imported_sr != generated_sr:
        g = gcd(int(imported_sr), int(generated_sr))
        up = generated_sr // g
        down = imported_sr // g
        if imported.ndim == 1:
            imported = resample_poly(imported, up, down)
        else:
            imported = np.stack(
                [resample_poly(imported[:, ch], up, down) for ch in range(imported.shape[1])], axis=1
            )

    gen_stereo = to_stereo(generated)
    imp_stereo = to_stereo(imported)

    gen_len = gen_stereo.shape[0]
    imp_len = imp_stereo.shape[0]

    if imp_len < gen_len:
        reps = int(np.ceil(gen_len / imp_len))
        imp_stereo = np.tile(imp_stereo, (reps, 1))[:gen_len]
    else:
        imp_stereo = imp_stereo[:gen_len]

    mixed = mix_ratio * gen_stereo + (1 - mix_ratio) * imp_stereo
    peak = np.max(np.abs(mixed))
    if peak > 0.98:
        mixed = mixed * (0.98 / peak)

    return mixed.astype(np.float32)


def write_wav(signal, sr: int, out_path: str):
    peak = np.max(np.abs(signal)) if signal.size else 0
    if peak > 0.999:
        signal = signal * (0.999 / peak)
    int16_data = (signal * 32767).astype(np.int16)
    wavfile.write(out_path, sr, int16_data)
    return out_path
