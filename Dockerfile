# ============================================================
# AirScribe — Enterprise Offline Transcription
# Multi-stage build: download models, then build runtime image
# ============================================================

# Stage 1: Model downloader
FROM python:3.11-slim AS model-downloader

RUN pip install --no-cache-dir faster-whisper

ARG WHISPER_MODEL=large-v3
ENV WHISPER_CACHE=/models/whisper

COPY scripts/download_models.sh /scripts/download_models.sh
RUN chmod +x /scripts/download_models.sh && /scripts/download_models.sh ${WHISPER_MODEL}

# Stage 2: Runtime
FROM python:3.11-slim AS runtime

# System deps for audio processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY pyproject.toml .
COPY src/ src/
RUN pip install --no-cache-dir .

# Copy pre-downloaded models
COPY --from=model-downloader /models /models
ENV WHISPER_CACHE=/models/whisper
ENV AIRSCRIBE_MODEL=large-v3
ENV AIRSCRIBE_DEVICE=cpu

# Default: run API server
EXPOSE 8080
ENTRYPOINT ["airscribe"]
CMD ["serve", "--port", "8080"]
