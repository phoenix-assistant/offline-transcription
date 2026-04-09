# AirScribe

**Enterprise offline speech-to-text for air-gapped environments.**

Zero internet required post-deploy. Powered by [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (large-v3) with speaker diarization via [pyannote.audio](https://github.com/pyannote/pyannote-audio).

## Features

- 🔒 **Fully offline** — all models bundled, no network calls after deployment
- 🎤 **Speaker diarization** — identify 2-20 speakers automatically
- 📚 **Domain presets** — medical, legal, military vocabulary built-in
- 📝 **Custom vocabulary** — inject domain-specific terms for accuracy
- 📦 **Multiple output formats** — SRT, VTT, JSON, plain text, Markdown
- 🚀 **CLI + REST API** — single tool for scripts and services
- 🐳 **Docker-ready** — one image with everything included

## Quick Start

### Install

```bash
pip install .
```

### Transcribe

```bash
# Basic transcription
airscribe transcribe meeting.mp3

# With speaker diarization and custom vocabulary
airscribe transcribe meeting.mp3 --diarize --vocabulary medical_terms.txt --format md

# Batch processing
airscribe batch ./recordings/ --output ./transcripts/ --format srt

# Start REST API
airscribe serve --port 8080
```

## CLI Reference

### `airscribe transcribe`

```
airscribe transcribe <audio_file> [OPTIONS]

Options:
  -o, --output PATH          Output file (stdout if omitted)
  -f, --format TEXT          Output format: srt, vtt, json, txt, md
  -m, --model TEXT           Whisper model: tiny, base, small, medium, large-v2, large-v3
  -l, --language TEXT        Language code (auto-detect if omitted)
  --diarize                  Enable speaker diarization
  --min-speakers INT         Minimum speakers (default: 1)
  --max-speakers INT         Maximum speakers (default: 20)
  --vocabulary PATH          Custom vocabulary file (one term per line)
  --domain [medical|legal|military]  Domain preset
  --device TEXT              Device: auto, cpu, cuda
```

### `airscribe batch`

```
airscribe batch <input_dir> [OPTIONS]

Options:
  -o, --output PATH          Output directory (default: ./transcripts)
  -f, --format TEXT          Output format
  -m, --model TEXT           Whisper model
  --diarize                  Enable speaker diarization
  --vocabulary PATH          Custom vocabulary file
  --domain [medical|legal|military]  Domain preset
```

### `airscribe serve`

```
airscribe serve [OPTIONS]

Options:
  --host TEXT    Bind host (default: 0.0.0.0)
  -p, --port INT Bind port (default: 8080)
  -m, --model TEXT  Whisper model
  --device TEXT     Device: auto, cpu, cuda
```

## REST API

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/transcribe` | Transcribe uploaded audio |
| GET | `/models` | List available models |
| GET | `/domains` | List domain presets |

### Transcribe (multipart form)

```bash
curl -X POST http://localhost:8080/transcribe \
  -F "file=@meeting.mp3" \
  -F "format=json" \
  -F "diarize=true" \
  -F "domain=medical"
```

## Custom Vocabulary

Create a text file with one term per line:

```
# medical_terms.txt
myocardial infarction
electrocardiogram
thrombocytopenia
laparoscopic cholecystectomy
```

Use with `--vocabulary medical_terms.txt` or the `domain` form field in the API.

## Enterprise Deployment (Air-Gapped)

### Docker

```bash
# Build with models bundled (requires internet)
docker build -t airscribe:latest .

# Build with specific model
docker build --build-arg WHISPER_MODEL=medium -t airscribe:medium .

# Export for air-gap transfer
docker save airscribe:latest | gzip > airscribe.tar.gz

# On air-gapped host
docker load < airscribe.tar.gz
docker run -p 8080:8080 airscribe:latest
```

### Docker Compose

```yaml
version: "3.8"
services:
  airscribe:
    image: airscribe:latest
    ports:
      - "8080:8080"
    volumes:
      - ./data:/data
    environment:
      - AIRSCRIBE_MODEL=large-v3
      - AIRSCRIBE_DEVICE=cpu
    deploy:
      resources:
        limits:
          memory: 8G
```

### Hardware Requirements

| Model | RAM | VRAM (GPU) | Disk |
|-------|-----|------------|------|
| tiny | 1 GB | 1 GB | 150 MB |
| base | 1 GB | 1 GB | 300 MB |
| small | 2 GB | 2 GB | 1 GB |
| medium | 5 GB | 5 GB | 3 GB |
| large-v3 | 10 GB | 10 GB | 6 GB |

### Pre-download Models

```bash
# Run on internet-connected machine
./scripts/download_models.sh large-v3

# Models cached to /models/whisper — copy to air-gapped host
```

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check src/
```

## License

MIT
