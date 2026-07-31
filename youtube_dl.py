"""YouTube URL -> wav download, using yt-dlp + ffmpeg.

YouTube increasingly blocks the default "web" client with a
"Sign in to confirm you're not a bot" error, especially from datacenter IPs
(which is exactly what a Render server is). yt-dlp's known workaround is to
request other player clients (android/ios/tv) that don't trigger the same
check, tried in order until one works. If YouTube tightens this further and
all clients start failing, the real fix is supplying browser cookies (see
COOKIES_FILE below) - that's a bigger lift so it's not wired in by default.
"""
import os
import re
import shutil
import uuid

YOUTUBE_URL_RE = re.compile(
    r"^https?://(www\.)?(youtube\.com/(watch\?v=|shorts/)|youtu\.be/)[\w-]+", re.IGNORECASE
)

# Optional: path to a Netscape-format cookies.txt file (exported from a
# logged-in browser session) for when player-client spoofing alone isn't
# enough. Not required for normal operation - only set this if downloads
# keep failing with a bot-check error even after the client fallback below.
COOKIES_FILE = os.environ.get("YOUTUBE_COOKIES_FILE")

# Player clients to try, in order. "web" has the fullest format list
# (including separate audio-only streams) but gets bot-check-blocked without
# cookies; android/ios dodge the bot-check but often expose a narrower,
# sometimes audio-less format list. With cookies configured, try web first
# since it's both authenticated and has the best format selection; without
# cookies, lead with the clients that don't need auth to at least work.
PLAYER_CLIENT_ATTEMPTS = (
    [["web", "tv"], ["android"], ["ios"]]
    if COOKIES_FILE
    else [["android"], ["ios"], ["web", "tv"]]
)


class YouTubeDownloadError(Exception):
    pass


def is_youtube_url(url: str) -> bool:
    return bool(YOUTUBE_URL_RE.match(url.strip()))


def _writable_cookies_copy(work_dir: str) -> str:
    """yt-dlp writes updated cookies back to whatever file it's given (to
    persist session refreshes), but Render's Secret Files are mounted
    read-only - so point it at a writable copy instead of the original."""
    dest = os.path.join(work_dir, "_yt_cookies_writable.txt")
    if not os.path.exists(dest) or os.path.getmtime(COOKIES_FILE) > os.path.getmtime(dest):
        shutil.copyfile(COOKIES_FILE, dest)
    return dest


def _base_opts(work_dir: str, job_id: str):
    out_template = os.path.join(work_dir, f"yt_{job_id}.%(ext)s")
    opts = {
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
    if COOKIES_FILE and os.path.exists(COOKIES_FILE):
        opts["cookiefile"] = _writable_cookies_copy(work_dir)
    return opts


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
    last_error = None

    for clients in PLAYER_CLIENT_ATTEMPTS:
        ydl_opts = _base_opts(work_dir, job_id)
        ydl_opts["extractor_args"] = {"youtube": {"player_client": clients}}
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            expected_wav = os.path.join(work_dir, f"yt_{job_id}.wav")
            if os.path.exists(expected_wav):
                return expected_wav
            for f in os.listdir(work_dir):
                if f.startswith(f"yt_{job_id}"):
                    return os.path.join(work_dir, f)
        except Exception as e:
            last_error = e
            continue

    raise YouTubeDownloadError(
        f"Could not download audio from that URL after trying multiple methods: {last_error}"
    )
