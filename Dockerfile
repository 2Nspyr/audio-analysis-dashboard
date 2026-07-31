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

CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 300 app:app"]
