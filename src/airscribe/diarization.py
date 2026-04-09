"""Speaker diarization pipeline using pyannote.audio."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from .transcriber import Segment, TranscriptionResult

logger = logging.getLogger(__name__)


class DiarizationPipeline:
    """Speaker diarization using pyannote.audio."""

    def __init__(self, model_name: str = "pyannote/speaker-diarization-3.1", auth_token: Optional[str] = None):
        self.model_name = model_name
        self.auth_token = auth_token
        self._pipeline = None

    def _load(self) -> None:
        if self._pipeline is not None:
            return
        from pyannote.audio import Pipeline

        logger.info("Loading diarization model %s", self.model_name)
        self._pipeline = Pipeline.from_pretrained(self.model_name, use_auth_token=self.auth_token)

        import torch
        if torch.cuda.is_available():
            self._pipeline.to(torch.device("cuda"))

    def diarize(
        self,
        audio_path: str | Path,
        min_speakers: int = 1,
        max_speakers: int = 20,
    ) -> list[dict]:
        """Run diarization, return list of {start, end, speaker}."""
        self._load()
        result = self._pipeline(
            str(audio_path),
            min_speakers=min_speakers,
            max_speakers=max_speakers,
        )
        turns = []
        for turn, _, speaker in result.itertracks(yield_label=True):
            turns.append({"start": turn.start, "end": turn.end, "speaker": speaker})
        return turns

    def assign_speakers(
        self,
        transcription: TranscriptionResult,
        diarization_turns: list[dict],
    ) -> TranscriptionResult:
        """Assign speaker labels to transcription segments based on overlap."""
        for seg in transcription.segments:
            seg.speaker = self._find_speaker(seg.start, seg.end, diarization_turns)
        return transcription

    @staticmethod
    def _find_speaker(start: float, end: float, turns: list[dict]) -> Optional[str]:
        """Find the speaker with the most overlap for a given time range."""
        best_speaker = None
        best_overlap = 0.0
        for turn in turns:
            overlap_start = max(start, turn["start"])
            overlap_end = min(end, turn["end"])
            overlap = max(0.0, overlap_end - overlap_start)
            if overlap > best_overlap:
                best_overlap = overlap
                best_speaker = turn["speaker"]
        return best_speaker
