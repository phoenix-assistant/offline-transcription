"""FastAPI REST API for AirScribe."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse

from .transcriber import Transcriber, TranscriptionResult, DOMAIN_PRESETS
from .diarization import DiarizationPipeline
from .formatters import format_output

app = FastAPI(
    title="AirScribe",
    description="Enterprise offline speech-to-text API",
    version="0.1.0",
)

_transcriber: Optional[Transcriber] = None
_diarizer: Optional[DiarizationPipeline] = None


def get_transcriber() -> Transcriber:
    global _transcriber
    if _transcriber is None:
        model = os.environ.get("AIRSCRIBE_MODEL", "large-v3")
        device = os.environ.get("AIRSCRIBE_DEVICE", "auto")
        _transcriber = Transcriber(model_size=model, device=device)
    return _transcriber


def get_diarizer() -> DiarizationPipeline:
    global _diarizer
    if _diarizer is None:
        _diarizer = DiarizationPipeline()
    return _diarizer


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}


@app.post("/transcribe")
async def transcribe(
    file: UploadFile = File(...),
    format: str = Form("json"),
    language: Optional[str] = Form(None),
    diarize: bool = Form(False),
    min_speakers: int = Form(1),
    max_speakers: int = Form(20),
    domain: Optional[str] = Form(None),
):
    """Transcribe an uploaded audio file."""
    if domain and domain not in DOMAIN_PRESETS:
        raise HTTPException(400, f"Unknown domain: {domain}. Options: {list(DOMAIN_PRESETS.keys())}")

    # Save uploaded file to temp location
    suffix = Path(file.filename or "audio.wav").suffix
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        transcriber = get_transcriber()
        if domain:
            transcriber.set_vocabulary(domain=domain)

        result = transcriber.transcribe(tmp_path, language=language)

        if diarize:
            diarizer = get_diarizer()
            turns = diarizer.diarize(tmp_path, min_speakers=min_speakers, max_speakers=max_speakers)
            result = diarizer.assign_speakers(result, turns)

        formatted = format_output(result, format)

        if format == "json":
            return JSONResponse(content=result.to_dict())
        return PlainTextResponse(content=formatted)
    finally:
        os.unlink(tmp_path)


@app.get("/models")
async def list_models():
    return {
        "available": ["tiny", "base", "small", "medium", "large-v2", "large-v3"],
        "current": os.environ.get("AIRSCRIBE_MODEL", "large-v3"),
    }


@app.get("/domains")
async def list_domains():
    return {name: len(terms) for name, terms in DOMAIN_PRESETS.items()}
