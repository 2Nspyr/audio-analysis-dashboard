"""Spectrogram generation using scipy.signal.stft + matplotlib (no librosa)."""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.signal import stft


def generate_spectrogram_image(mono: np.ndarray, sr: int, out_path: str,
                                 nperseg: int = 2048, max_freq: int = 8000):
    f, t, Zxx = stft(mono, fs=sr, nperseg=nperseg, noverlap=nperseg // 2)
    mag = np.abs(Zxx)
    mag_db = 20 * np.log10(mag + 1e-10)

    freq_mask = f <= max_freq
    f_plot = f[freq_mask]
    mag_db_plot = mag_db[freq_mask, :]

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
