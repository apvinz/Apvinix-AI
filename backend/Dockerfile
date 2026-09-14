FROM python:3.11-slim

# System dependencies: ffmpeg is required for audio_processor.py
# (ffprobe/ffmpeg normalization); build-essential + libsndfile1 are needed
# for librosa/soundfile/scipy wheels to install/run cleanly.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy the actual application code
COPY app ./app
COPY check_environment.py .

# Data dirs used by job_manager.py for uploads/processing/outputs.
# NOTE: this is local disk storage and is EPHEMERAL on most PaaS free
# tiers (Render/Railway) — it resets on every redeploy/restart. Fine for
# an MVP, but move to S3-compatible object storage before relying on
# results persisting long-term.
RUN mkdir -p data/uploads data/processing data/outputs

# Render/Railway inject $PORT at runtime; default to 8000 for local docker run.
ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
