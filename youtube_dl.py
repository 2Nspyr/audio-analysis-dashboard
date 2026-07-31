"""YouTube URL -> wav download, using yt-dlp + ffmpeg.

NOTE: yt-dlp is not installable in the dev sandbox this was built in (no
PyPI access there), so this module is untested locally. It will run in any
environment where `pip install yt-dlp` succeeded (e.g. Render's build,
which has full internet access) and ffmpeg is on PATH. The code follows
yt-dlp's standard documented API, so it should work, but it's flagged here
as the one part of this build that hasn't been verified against a real
download in this session - test it first thing after deploying.
"""
import os
import re
import uuid

YOUTUBE_URL_RE = re.compile(
    r"^https?://(www\.)?(youtube\.com/(watch\?v=|shorts/)|youtu\.be/)[\w-]+", re.IGNORECASE
)


class YouTubeDownloadError(Exception):
    pass


def is_youtube_url(url: str) -> bool:
    return bool(YOUTUBE_URL_RE.match(url.strip()))


def download_audio(url: str, work_dir: str) -> str:
    """Downloads the audio track from a YouTube URL and returns the path to
    a wav file. Raises YouTubeDownloadError on failure."""
    try:
        import yt_dlp
    except ImportError as e:
        raise YouTubeDownloadError(
            "yt-dlp is not installed in this environment. Add 'yt-dlp' to requirements.txt "
            "and make sure the deploy target has internet access during build."
        ) from e

    job_id = uuid.uuid4().hex[:12]
    out_template = os.path.join(work_dir, f"yt_{job_id}.%(ext)s")

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": out_template,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "wav",
            "preferredquality": "0",
        }],
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as e:
        raise YouTubeDownloadError(f"Could not download audio from that URL: {e}") from e

    expected_wav = os.path.join(work_dir, f"yt_{job_id}.wav")
    if os.path.exists(expected_wav):
        return expected_wav

    for f in os.listdir(work_dir):
        if f.startswith(f"yt_{job_id}"):
            return os.path.join(work_dir, f)

    raise YouTubeDownloadError("Download completed but no output file was found.")
