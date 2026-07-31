"""Shared DSP helpers."""
import numpy as np
from scipy.signal import decimate

# scipy.signal.decimate's memory cost scales with the FULL input length, not
# just the filter order - profiling a single decimate() call on a 25-minute
# track's worth of samples (30M) showed a >100MB spike despite float32 input
# and zero_phase=False, regardless of the modest output size. Running it in
# fixed-size chunks instead bounds that spike to roughly one chunk's worth
# no matter how long the track is (this app's real use case is 20-40 minute
# sessions). A small overlap between chunks (discarded after filtering) keeps
# the anti-alias filter's edge transient from creating an audible/measurable
# artifact at each chunk boundary.
_CHUNK_SAMPLES = 2_000_000
_OVERLAP_SAMPLES = 4_000


def _decimate_chunked(x: np.ndarray, q: int) -> np.ndarray:
    n = len(x)
    if n <= _CHUNK_SAMPLES:
        return decimate(x, q, zero_phase=False)

    out_chunks = []
    pos = 0
    while pos < n:
        end = min(pos + _CHUNK_SAMPLES, n)
        lo = max(0, pos - _OVERLAP_SAMPLES)
        hi = min(n, end + _OVERLAP_SAMPLES)
        piece = decimate(x[lo:hi], q, zero_phase=False)

        # Trim off the overlap (converted to decimated-domain sample counts)
        # so chunks stitch back together at the same length decimating the
        # whole array at once would have produced.
        trim_lo = (pos - lo) // q
        trim_hi = (hi - end) // q
        if trim_hi > 0:
            piece = piece[trim_lo: -trim_hi if trim_hi else None]
        else:
            piece = piece[trim_lo:]
        out_chunks.append(piece)
        pos = end

    return np.concatenate(out_chunks)


def cascade_decimate(x: np.ndarray, sr: float, target_sr: float):
    """Downsample x from sr to approximately target_sr using cascaded
    decimation (factor <=10 per stage, scipy's recommended limit for stable
    IIR anti-aliasing). Returns (downsampled_array, actual_sr) - actual_sr
    may differ slightly from target_sr since only integer factors are used.
    No-op (returns x, sr unchanged) if sr is already <= target_sr.
    """
    if sr <= target_sr:
        return x, sr
    # Keep float32 instead of upcasting to float64: scipy.signal.decimate's
    # filtfilt works fine at float32 precision for audio, and forcing
    # float64 here was silently doubling the memory footprint of every
    # decimate call (the biggest single spike observed in memory profiling
    # was inside this function, not the caller).
    if x.dtype != np.float32:
        x = x.astype(np.float32)
    cur_sr = float(sr)
    # zero_phase=True runs the anti-alias filter forward AND backward
    # (filtfilt) to cancel phase distortion - for a long track that measured
    # as THE single biggest memory spike in the whole pipeline (+344MB on a
    # 25-minute file in profiling), well beyond what the output array size
    # would suggest. None of this app's analyses (pitch tracking, spectrogram
    # magnitude, Welch peak-finding) care about phase or exact sample timing,
    # so the single-pass filter (zero_phase=False) is a safe trade: same
    # anti-aliasing quality, roughly a third of the memory.
    while cur_sr / target_sr > 10:
        x = _decimate_chunked(x, 10)
        cur_sr /= 10
    factor = max(1, int(round(cur_sr / target_sr)))
    if factor > 1:
        x = _decimate_chunked(x, factor)
        cur_sr /= factor
    return x, cur_sr
