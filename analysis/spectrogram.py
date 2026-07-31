"""Spectrogram generation using scipy.signal.stft + matplotlib (no librosa)."""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.signal import stft
from analysis.dsp_utils import cascade_decimate


def generate_spectrogram_image(mono: np.ndarray, sr: int, out_path: str,
                                 nperseg: int = 2048, max_freq: int = 8000):
    # We only ever plot up to max_freq, so running the STFT at full sample
    # rate wastes most of its resolution and memory on frequencies we throw
    # away. ~2.2x max_freq keeps comfortable headroom above the Nyquist rate
    # actually needed for max_freq.
    ds, ds_sr = cascade_decimate(mono, sr, max_freq * 2.2)
    nperseg = min(nperseg, len(ds))

    f, t, Zxx = stft(ds, fs=ds_sr, nperseg=nperseg, noverlap=nperseg // 2)

    # Mask down to the display range BEFORE computing abs/log10, so the
    # full-width magnitude/dB arrays (which this STFT config could size in
    # the hundreds of MB for a long track) never get allocated at all.
    freq_mask = f <= max_freq
    f_plot = f[freq_mask]
    Zxx_plot = Zxx[freq_mask, :]
    del Zxx

    mag_db_plot = 20 * np.log10(np.abs(Zxx_plot) + 1e-10)
    del Zxx_plot

    vmax = mag_db_plot.max()
    vmin = vmax - 80  # 80 dB dynamic range

    fig, ax = plt.subplots(figsize=(10, 4), dpi=110)
    im = ax.pcolormesh(t, f_plot, mag_db_plot, shading="auto", cmap="inferno",
                        vmin=vmin, vmax=vmax)
    ax.set_ylabel("Frequency (Hz)")
    ax.set_xlabel("Time (s)")
    ax.set_title("Spectrogram")
    fig.colorbar(im, ax=ax, label="dB")
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)
    return out_path
