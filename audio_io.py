"""Audio I/O helpers. Uses ffmpeg (already on the system) to normalize any
input file (mp3/wav/whatever) to a clean PCM wav, then reads it with
scipy.io.wavfile. Avoids any dependency on librosa/soundfile, neither of
which is installable in this environment right now.
"""
import os
import subprocess
import numpy as np
from scipy.io import wavfile

# No analysis stage in this app needs more than ~8kHz of bandwidth (the
# spectrogram's display ceiling), so there's no reason to ever hold the
# original 44.1/48kHz audio in memory. The per-stage downsampling added
# earlier (dsp_utils.cascade_decimate) only shrinks *local copies* inside
# each analysis function - the full-resolution `data`/`mono` arrays loaded
# here still sit in memory for the ENTIRE report build, across all 5
# analysis stages. For a 20-minute stereo track at 44.1kHz that's roughly
# ~630MB in float32 alone (stereo + mono downmix), which exceeds Render's
# free-tier 512MB limit before a single analysis stage even runs - this is
# the real OOM cause. Converting via ffmpeg directly to a much lower sample
# rate shrinks that base footprint by >2x with zero loss of anything the
# app actually uses (20kHz gives ~10kHz of headroom above the highest
# frequency any analysis stage looks at).
TARGET_SR = 20000


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

    # `raw.astype(np.float32) / N` allocates the float32 array AND a second
    # full-size array for the division result - for a 25-minute stereo file
    # that was a ~460MB spike on its own (confirmed in memory profiling:
    # this single line was the single biggest allocation in the entire
    # pipeline). In-place division (`/=`) reuses the same buffer instead of
    # allocating a second one.
    if raw.dtype == np.int16:
        data = raw.astype(np.float32)
        data /= 32768.0
    elif raw.dtype == np.int32:
        data = raw.astype(np.float32)
        data /= 2147483648.0
    elif raw.dtype == np.uint8:
        data = raw.astype(np.float32)
        data -= 128.0
        data /= 128.0
    else:
        data = raw.astype(np.float32)
    del raw  # drop the int PCM copy now that we have the float32 version

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
