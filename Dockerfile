FROM python:3.11-slim

# ffmpeg is required for audio format conversion (uploads + YouTube downloads).
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p static/uploads static/reports static/work

ENV PORT=5050
EXPOSE 5050

# --workers 1 --threads 8: this app keeps job/report state in an in-process
# dict (no database - it's a personal single-user tool). Multiple gunicorn
# *worker processes* each get their own separate memory, so a job created
# in one worker would be invisible to a status poll that lands on another
# worker - one process with multiple threads keeps everything visible to
# every request while still handling requests concurrently.
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 8 --timeout 300 app:app"]
