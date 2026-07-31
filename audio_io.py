"""Audio I/O helpers. Uses ffmpeg (already on the system) to normalize any
input file (mp3/wav/whatever) to a clean PCM wav, then reads it with
scipy.io.wavfile. Avoids any dependency on librosa/soundfile, neither of
which is installable in this environment right now.
"""
import os
import subprocess
import numpy as np
from scipy.io import wavfile

TARGET_SR = 44100


class AudioLoadError(Exception):
    pass


def convert_to_wav(input_path: str, out_path: str, target_sr: int = TARGET_SR) -> None:
    """Convert any input audio file to 16-bit PCM wav at target_sr, preserving
    the original channel count (mono stays mono, stereo stays stereo)."""
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-ar", str(target_sr),
        "-sample_fmt", "s16",
        "-vn",
        out_path,
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0 or not os.path.exists(out_path):
        raise AudioLoadError(
            f"ffmpeg failed to convert {input_path}: {proc.stderr.decode(errors='ignore')[-2000:]}"
        )


def load_audio(input_path: str, work_dir: str):
    """Convert + load an audio file. Returns a dict with:
    sr, data (float32, shape (n,) mono or (n, ch) stereo, range -1..1),
    channels, duration_sec, mono (float32 downmix for pitch/spectral work).
    """
    base = os.path.splitext(os.path.basename(input_path))[0]
    wav_path = os.path.join(work_dir, base + "_norm.wav")
    convert_to_wav(input_path, wav_path)

    sr, raw = wavfile.read(wav_path)

    if raw.dtype == np.int16:
        data = raw.astype(np.float32) / 32768.0
    elif raw.dtype == np.int32:
        data = raw.astype(np.float32) / 2147483648.0
    elif raw.dtype == np.uint8:
        data = (raw.astype(np.float32) - 128.0) / 128.0
    else:
        data = raw.astype(np.float32)

    if data.ndim == 1:
        channels = 1
        mono = data
    else:
        channels = data.shape[1]
        mono = data.mean(axis=1)

    duration_sec = len(mono) / float(sr)

    return {
        "sr": sr,
        "data": data,
        "channels": channels,
        "duration_sec": duration_sec,
        "mono": mono,
        "wav_path": wav_path,
    }
