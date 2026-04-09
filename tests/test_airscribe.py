"""Tests for AirScribe — unit tests that don't require model downloads."""

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from airscribe.transcriber import Segment, TranscriptionResult, DOMAIN_PRESETS
from airscribe.vocabulary import VocabularyProcessor
from airscribe.formatters import to_srt, to_vtt, to_json, to_text, to_markdown, format_output
from airscribe.diarization import DiarizationPipeline


# --- Fixtures ---

@pytest.fixture
def sample_result():
    return TranscriptionResult(
        segments=[
            Segment(start=0.0, end=2.5, text="Hello world", speaker="SPEAKER_00", confidence=-0.3),
            Segment(start=2.5, end=5.0, text="How are you", speaker="SPEAKER_01", confidence=-0.2),
            Segment(start=5.0, end=8.0, text="I am fine", speaker="SPEAKER_00", confidence=-0.1),
        ],
        language="en",
        language_probability=0.98,
        duration=8.0,
        text="Hello world How are you I am fine",
    )


@pytest.fixture
def result_no_speakers():
    return TranscriptionResult(
        segments=[
            Segment(start=0.0, end=3.0, text="First segment"),
            Segment(start=3.0, end=6.0, text="Second segment"),
        ],
        language="en",
        language_probability=0.95,
        duration=6.0,
        text="First segment Second segment",
    )


# --- VocabularyProcessor Tests ---

class TestVocabularyProcessor:
    def test_apply_corrections(self):
        vp = VocabularyProcessor(["myocardial infarction", "ECG"])
        assert vp.apply("The ecg showed myocardial infarction") == "The ECG showed myocardial infarction"

    def test_as_prompt(self):
        vp = VocabularyProcessor(["term1", "term2"])
        prompt = vp.as_prompt()
        assert "term1" in prompt
        assert "term2" in prompt
        assert prompt.startswith("Vocabulary:")

    def test_load_file(self, tmp_path):
        vocab_file = tmp_path / "vocab.txt"
        vocab_file.write_text("alpha\nbeta\n# comment\n\ngamma\n")
        terms = VocabularyProcessor.load_file(vocab_file)
        assert terms == ["alpha", "beta", "gamma"]

    def test_empty_vocabulary(self):
        vp = VocabularyProcessor([])
        assert vp.apply("unchanged text") == "unchanged text"


# --- Formatter Tests ---

class TestSRTFormatter:
    def test_basic_srt(self, sample_result):
        srt = to_srt(sample_result)
        assert "1\n00:00:00,000 --> 00:00:02,500" in srt
        assert "[SPEAKER_00] Hello world" in srt
        assert "[SPEAKER_01] How are you" in srt

    def test_srt_no_speakers(self, result_no_speakers):
        srt = to_srt(result_no_speakers)
        assert "First segment" in srt
        assert "[" not in srt  # No speaker tags


class TestVTTFormatter:
    def test_basic_vtt(self, sample_result):
        vtt = to_vtt(sample_result)
        assert vtt.startswith("WEBVTT")
        assert "00:00:00.000 --> 00:00:02.500" in vtt
        assert "<v SPEAKER_00>Hello world" in vtt


class TestJSONFormatter:
    def test_valid_json(self, sample_result):
        output = to_json(sample_result)
        data = json.loads(output)
        assert data["language"] == "en"
        assert len(data["segments"]) == 3
        assert data["segments"][0]["speaker"] == "SPEAKER_00"


class TestTextFormatter:
    def test_with_speakers(self, sample_result):
        text = to_text(sample_result)
        assert "[SPEAKER_00]" in text
        assert "[SPEAKER_01]" in text

    def test_without_speakers(self, result_no_speakers):
        text = to_text(result_no_speakers)
        assert "[" not in text
        assert "First segment" in text


class TestMarkdownFormatter:
    def test_markdown_header(self, sample_result):
        md = to_markdown(sample_result)
        assert "# Transcription" in md
        assert "**Language:** en" in md
        assert "### SPEAKER_00" in md


class TestFormatOutput:
    def test_unknown_format_raises(self, sample_result):
        with pytest.raises(ValueError, match="Unknown format"):
            format_output(sample_result, "pdf")

    def test_all_formats(self, sample_result):
        for fmt in ["srt", "vtt", "json", "txt", "text", "md", "markdown"]:
            output = format_output(sample_result, fmt)
            assert len(output) > 0


# --- Diarization Tests ---

class TestDiarizationAssignment:
    def test_assign_speakers(self):
        pipeline = DiarizationPipeline.__new__(DiarizationPipeline)
        result = TranscriptionResult(
            segments=[
                Segment(start=0.0, end=2.0, text="Hello"),
                Segment(start=2.0, end=4.0, text="World"),
            ],
            language="en", language_probability=0.9, duration=4.0, text="Hello World",
        )
        turns = [
            {"start": 0.0, "end": 2.5, "speaker": "A"},
            {"start": 2.5, "end": 5.0, "speaker": "B"},
        ]
        result = pipeline.assign_speakers(result, turns)
        assert result.segments[0].speaker == "A"
        assert result.segments[1].speaker == "B"

    def test_find_speaker_no_overlap(self):
        speaker = DiarizationPipeline._find_speaker(10.0, 12.0, [
            {"start": 0.0, "end": 5.0, "speaker": "A"},
        ])
        assert speaker is None


# --- TranscriptionResult Tests ---

class TestTranscriptionResult:
    def test_to_dict(self, sample_result):
        d = sample_result.to_dict()
        assert d["language"] == "en"
        assert len(d["segments"]) == 3
        assert d["duration"] == 8.0

    def test_empty_result(self):
        r = TranscriptionResult()
        d = r.to_dict()
        assert d["segments"] == []
        assert d["text"] == ""


# --- Domain Presets ---

class TestDomainPresets:
    def test_presets_exist(self):
        assert "medical" in DOMAIN_PRESETS
        assert "legal" in DOMAIN_PRESETS
        assert "military" in DOMAIN_PRESETS

    def test_presets_not_empty(self):
        for domain, terms in DOMAIN_PRESETS.items():
            assert len(terms) > 0, f"{domain} preset is empty"
