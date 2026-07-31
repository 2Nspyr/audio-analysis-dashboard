"""Shared DSP helpers."""
import numpy as np
from scipy.signal import decimate


def cascade_decimate(x: np.ndarray, sr: float, target_sr: float):
    """Downsample x from sr to approximately target_sr using cascaded
    decimation (factor <=10 per stage, scipy's recommended limit for stable
    IIR anti-aliasing). Returns (downsampled_array, actual_sr) - actual_sr
    may differ slightly from target_sr since only integer factors are used.
    No-op (returns x, sr unchanged) if sr is already <= target_sr.
    """
    if sr <= target_sr:
        return x, sr
    x = np.asarray(x, dtype=np.float64)
    cur_sr = float(sr)
    while cur_sr / target_sr > 10:
        x = decimate(x, 10, zero_phase=True)
        cur_sr /= 10
    factor = max(1, int(round(cur_sr / target_sr)))
    if factor > 1:
        x = decimate(x, factor, zero_phase=True)
        cur_sr /= factor
    return x, cur_sr
