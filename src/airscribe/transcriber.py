"""Core transcription engine using faster-whisper."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from faster_whisper import WhisperModel

from .vocabulary import VocabularyProcessor

logger = logging.getLogger(__name__)

# Domain presets: curated vocabulary lists for specific industries
from typing import Dict, List

DOMAIN_PRESETS: Dict[str, List[str]] = {
    "medical": [
        "myocardial infarction", "electrocardiogram", "hemoglobin", "thrombocytopenia",
        "anesthesia", "laparoscopic", "metastasis", "biopsy", "catheterization",
        "intubation", "tachycardia", "bradycardia", "hemorrhage", "edema",
    ],
    "legal": [
        "habeas corpus", "voir dire", "amicus curiae", "subpoena", "deposition",
        "plaintiff", "defendant", "injunction", "indictment", "tort",
        "jurisprudence", "adjudication", "affidavit", "arraignment",
    ],
    "military": [
        "SIGINT", "HUMINT", "COMINT", "ELINT", "OPSEC", "COMSEC",
        "CENTCOM", "SOCOM", "JSOC", "OPORD", "FRAGO", "SITREP",
        "exfiltration", "reconnaissance", "counterintelligence",
    ],
}


@dataclass
class Segment:
    """A single transcription segment."""

    start: float
    end: float
    text: str
    speaker: Optional[str] = None
    confidence: float = 0.0


@dataclass
class TranscriptionResult:
    """Complete transcription output."""

    segments: list[Segment] = field(default_factory=list)
    language: str = ""
    language_probability: float = 0.0
    duration: float = 0.0
    text: str = ""

    def to_dict(self) -> dict:
        return {
            "language": self.language,
            "language_probability": self.language_probability,
            "duration": self.duration,
            "text": self.text,
            "segments": [
                {
                    "start": s.start,
                    "end": s.end,
                    "text": s.text,
                    "speaker": s.speaker,
                    "confidence": s.confidence,
                }
                for s in self.segments
            ],
        }


class Transcriber:
    """Core transcription engine wrapping faster-whisper."""

    def __init__(
        self,
        model_size: str = "large-v3",
        device: str = "auto",
        compute_type: str = "auto",
    ):
        self.model_size = model_size
        if device == "auto":
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
        if compute_type == "auto":
            compute_type = "float16" if device == "cuda" else "int8"

        logger.info("Loading Whisper model %s on %s (%s)", model_size, device, compute_type)
        self.model = WhisperModel(model_size, device=device, compute_type=compute_type)
        self._vocab_processor: Optional[VocabularyProcessor] = None

    def set_vocabulary(
        self,
        vocabulary_file: Optional[Path] = None,
        domain: Optional[str] = None,
        extra_terms: Optional[list[str]] = None,
    ) -> None:
        """Configure custom vocabulary for post-processing."""
        terms: list[str] = []
        if vocabulary_file:
            terms.extend(VocabularyProcessor.load_file(vocabulary_file))
        if domain and domain in DOMAIN_PRESETS:
            terms.extend(DOMAIN_PRESETS[domain])
        if extra_terms:
            terms.extend(extra_terms)
        if terms:
            self._vocab_processor = VocabularyProcessor(terms)

    def transcribe(
        self,
        audio_path: str | Path,
        language: Optional[str] = None,
        initial_prompt: Optional[str] = None,
    ) -> TranscriptionResult:
        """Transcribe an audio file."""
        audio_path = str(audio_path)

        # Build initial prompt from vocabulary if available
        if initial_prompt is None and self._vocab_processor:
            initial_prompt = self._vocab_processor.as_prompt()

        segments_gen, info = self.model.transcribe(
            audio_path,
            language=language,
            initial_prompt=initial_prompt,
            vad_filter=True,
            word_timestamps=True,
        )

        segments: list[Segment] = []
        full_text_parts: list[str] = []
        for seg in segments_gen:
            text = seg.text.strip()
            if self._vocab_processor:
                text = self._vocab_processor.apply(text)
            segments.append(
                Segment(
                    start=seg.start,
                    end=seg.end,
                    text=text,
                    confidence=seg.avg_logprob,
                )
            )
            full_text_parts.append(text)

        return TranscriptionResult(
            segments=segments,
            language=info.language,
            language_probability=info.language_probability,
            duration=info.duration,
            text=" ".join(full_text_parts),
        )
