"""In-memory background job tracking for long-running analysis/download work.

Why this exists: analyzing a real 20-40 minute file (or downloading + analyzing
a YouTube video) can take well past a typical reverse-proxy timeout if done
synchronously inside one HTTP request - that's what was producing 502s. Instead
the request that kicks off the work returns almost immediately with a job id,
a background thread does the actual work and updates this store as it goes,
and the browser polls a small status endpoint to show progress and redirect
once done.

This is intentionally simple (a dict + a lock, no persistence) - fine for a
personal single-user tool. See the Dockerfile for why gunicorn is run with a
single worker process (multiple *processes* would each have their own copy
of this dict).
"""
import threading
import time
import uuid

_lock = threading.Lock()
_jobs = {}

STAGES = [
    "starting",
    "loading audio",
    "tuning reference",
    "spectrogram",
    "binaural beat",
    "isochronic pulse",
    "harmonic balance",
    "done",
]


def create_job(kind: str) -> str:
    job_id = uuid.uuid4().hex[:12]
    with _lock:
        _jobs[job_id] = {
            "id": job_id,
            "kind": kind,  # "analyze" | "analyze_url" | "generate"
            "status": "processing",  # processing | done | error
            "stage": "starting",
            "created_at": time.time(),
            "error": None,
            "redirect_url": None,
        }
    return job_id


def update_job(job_id: str, **kwargs):
    with _lock:
        if job_id in _jobs:
            _jobs[job_id].update(kwargs)


def get_job(job_id: str):
    with _lock:
        job = _jobs.get(job_id)
        return dict(job) if job else None


def set_stage(job_id: str, stage: str):
    update_job(job_id, stage=stage)


def set_done(job_id: str, redirect_url: str):
    update_job(job_id, status="done", stage="done", redirect_url=redirect_url)


def set_error(job_id: str, message: str):
    update_job(job_id, status="error", error=message)
