#!/usr/bin/env bash
# Download Whisper models for offline/air-gapped deployment.
# Usage: ./scripts/download_models.sh [model_size]
#   model_size: tiny, base, small, medium, large-v2, large-v3 (default: large-v3)

set -euo pipefail

MODEL_SIZE="${1:-large-v3}"
CACHE_DIR="${WHISPER_CACHE:-/models/whisper}"

echo "Downloading faster-whisper model: ${MODEL_SIZE}"
python3 -c "
from faster_whisper import WhisperModel
import os
os.makedirs('${CACHE_DIR}', exist_ok=True)
# This triggers the model download and caching
model = WhisperModel('${MODEL_SIZE}', device='cpu', compute_type='int8',
                     download_root='${CACHE_DIR}')
print('Model downloaded successfully')
"

echo "Model cached to ${CACHE_DIR}"
echo "Done. Ready for air-gap deployment."
