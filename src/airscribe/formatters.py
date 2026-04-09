"""Output formatters: SRT, VTT, JSON, plain text, Markdown."""

from __future__ import annotations

import json
from .transcriber import TranscriptionResult


def _format_time_srt(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _format_time_vtt(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def to_srt(result: TranscriptionResult) -> str:
    lines = []
    for i, seg in enumerate(result.segments, 1):
        speaker = f"[{seg.speaker}] " if seg.speaker else ""
        lines.append(str(i))
        lines.append(f"{_format_time_srt(seg.start)} --> {_format_time_srt(seg.end)}")
        lines.append(f"{speaker}{seg.text}")
        lines.append("")
    return "\n".join(lines)


def to_vtt(result: TranscriptionResult) -> str:
    lines = ["WEBVTT", ""]
    for i, seg in enumerate(result.segments, 1):
        speaker = f"<v {seg.speaker}>" if seg.speaker else ""
        lines.append(str(i))
        lines.append(f"{_format_time_vtt(seg.start)} --> {_format_time_vtt(seg.end)}")
        lines.append(f"{speaker}{seg.text}")
        lines.append("")
    return "\n".join(lines)


def to_json(result: TranscriptionResult) -> str:
    return json.dumps(result.to_dict(), indent=2, ensure_ascii=False)


def to_text(result: TranscriptionResult) -> str:
    lines = []
    current_speaker = None
    for seg in result.segments:
        if seg.speaker and seg.speaker != current_speaker:
            current_speaker = seg.speaker
            lines.append(f"\n[{current_speaker}]")
        lines.append(seg.text)
    return "\n".join(lines).strip()


def to_markdown(result: TranscriptionResult) -> str:
    lines = [
        "# Transcription",
        "",
        f"**Language:** {result.language} ({result.language_probability:.0%})",
        f"**Duration:** {result.duration:.1f}s",
        "",
        "---",
        "",
    ]
    current_speaker = None
    for seg in result.segments:
        if seg.speaker and seg.speaker != current_speaker:
            current_speaker = seg.speaker
            lines.append(f"\n### {current_speaker}\n")
        ts = _format_time_vtt(seg.start)
        lines.append(f"**[{ts}]** {seg.text}")
    return "\n".join(lines)


FORMAT_MAP = {
    "srt": to_srt,
    "vtt": to_vtt,
    "json": to_json,
    "txt": to_text,
    "text": to_text,
    "md": to_markdown,
    "markdown": to_markdown,
}


def format_output(result: TranscriptionResult, fmt: str) -> str:
    formatter = FORMAT_MAP.get(fmt)
    if not formatter:
        raise ValueError(f"Unknown format: {fmt}. Supported: {list(FORMAT_MAP.keys())}")
    return formatter(result)
