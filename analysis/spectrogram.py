"""Spectrogram generation using scipy.signal.stft + matplotlib (no librosa)."""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.signal import stft
from scipy.signal.windows import hann
from analysis.dsp_utils import cascade_decimate

# Long tracks (this app's real use case is 20-40 minute sessions) turn into
# a LOT of STFT frames at once if run in a single scipy.signal.stft() call -
# scipy builds a full (nperseg x n_frames) windowed-segment array plus the
# complex FFT output before we get to mask/downsize anything, and on a
# ~30-minute track that intermediate alone measured several hundred MB in
# profiling (worse than any other single stage in the whole pipeline,
# reproduced locally: +260-400MB just for this call). Running the STFT over
# fixed-size time chunks instead bounds peak memory to roughly one chunk's
# worth, independent of total track length.
CHUNK_SEC = 60.0


def generate_spectrogram_image(mono: np.ndarray, sr: int, out_path: str,
                                 nperseg: int = 2048, max_freq: int = 8000):
    # We only ever plot up to max_freq, so running the STFT at full sample
    # rate wastes most of its resolution and memory on frequencies we throw
    # away. ~2.2x max_freq keeps comfortable headroom above the Nyquist rate
    # actually needed for max_freq.
    ds, ds_sr = cascade_decimate(mono, sr, max_freq * 2.2)
    nperseg = min(nperseg, len(ds))
    noverlap = nperseg // 2

    # Precompute the window as float32 explicitly - scipy's default window
    # construction is float64, and multiplying our float32 audio by a
    # float64 window silently upcasts every windowed segment (and the FFT
    # output) to double precision, roughly doubling memory for no benefit
    # at audio bit depths.
    window = hann(nperseg, sym=False).astype(np.float32)

    chunk_samples = max(int(CHUNK_SEC * ds_sr), nperseg * 4)
    hop = nperseg - noverlap

    # Figure out, up front, how many time columns the WHOLE track will
    # produce, and how much each chunk's columns need to be pooled down by
    # so the running total never exceeds the display target. Pooling inside
    # the loop (instead of concatenating every chunk at full STFT resolution
    # and downsampling once at the end) keeps this stage's memory flat
    # regardless of track length - a 5-minute file and a 40-minute file
    # (this app's real use case) both only ever hold ~MAX_TIME_BINS columns
    # at a time, rather than the full-length spectrogram scaling linearly
    # with duration before being thrown away.
    MAX_TIME_BINS = 1200
    n = len(ds)
    total_bins_estimate = max(1, 1 + (n - nperseg) // hop)
    pool_factor = max(1, int(np.ceil(total_bins_estimate / MAX_TIME_BINS)))

    f_plot = None
    mag_chunks = []
    t_chunks = []
    time_offset = 0.0
    carry_mag = None  # leftover columns (< pool_factor) carried into the next chunk
    carry_t = None

    pos = 0
    while pos < n:
        end = min(pos + chunk_samples, n)
        chunk = ds[pos:end]
        if len(chunk) < nperseg:
            break

        f, t, Zxx = stft(chunk, fs=ds_sr, window=window, nperseg=nperseg, noverlap=noverlap)

        if f_plot is None:
            freq_mask = f <= max_freq
            f_plot = f[freq_mask]

        Zxx_plot = Zxx[freq_mask, :]
        del Zxx
        mag = (20 * np.log10(np.abs(Zxx_plot) + 1e-10)).astype(np.float32)
        del Zxx_plot
        t = t + time_offset

        if carry_mag is not None:
            mag = np.concatenate([carry_mag, mag], axis=1)
            t = np.concatenate([carry_t, t])

        usable_cols = (mag.shape[1] // pool_factor) * pool_factor
        if usable_cols > 0:
            pooled = mag[:, :usable_cols].reshape(mag.shape[0], -1, pool_factor).max(axis=2)
            pooled_t = t[:usable_cols].reshape(-1, pool_factor).mean(axis=1)
            mag_chunks.append(pooled)
            t_chunks.append(pooled_t)

        if usable_cols < mag.shape[1]:
            carry_mag = mag[:, usable_cols:]
            carry_t = t[usable_cols:]
        else:
            carry_mag = None
            carry_t = None

        # Advance by less than the chunk length so consecutive chunks still
        # overlap by one window (keeps STFT frames continuous at the seam,
        # same as a single non-chunked call would produce).
        advance = chunk_samples - noverlap
        time_offset += advance / ds_sr
        pos += advance

    if carry_mag is not None and carry_mag.shape[1] > 0:
        mag_chunks.append(carry_mag.max(axis=1, keepdims=True))
        t_chunks.append(np.array([carry_t.mean()]))

    mag_db_plot = np.concatenate(mag_chunks, axis=1)
    del mag_chunks
    t = np.concatenate(t_chunks)
    del t_chunks

    vmax = mag_db_plot.max()
    vmin = vmax - 80  # 80 dB dynamic range

    fig, ax = plt.subplots(figsize=(10, 4), dpi=110)
    im = ax.imshow(mag_db_plot, aspect="auto", origin="lower", cmap="inferno",
                    extent=[t[0], t[-1], f_plot[0], f_plot[-1]], vmin=vmin, vmax=vmax)
    ax.set_ylabel("Frequency (Hz)")
    ax.set_xlabel("Time (s)")
    ax.set_title("Spectrogram")
    fig.colorbar(im, ax=ax, label="dB")
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)
    return out_path
