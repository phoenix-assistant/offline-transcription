"""CLI interface for AirScribe."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.progress import Progress

console = Console()


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.version_option(package_name="airscribe")
def main(verbose: bool) -> None:
    """AirScribe — Enterprise offline speech-to-text."""
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")


@main.command()
@click.argument("audio_file", type=click.Path(exists=True, path_type=Path))
@click.option("--output", "-o", type=click.Path(path_type=Path), help="Output file path")
@click.option("--format", "-f", "fmt", default="txt", help="Output format: srt, vtt, json, txt, md")
@click.option("--model", "-m", default="large-v3", help="Whisper model size")
@click.option("--language", "-l", default=None, help="Language code (auto-detect if omitted)")
@click.option("--diarize", is_flag=True, help="Enable speaker diarization")
@click.option("--min-speakers", default=1, help="Min speakers for diarization")
@click.option("--max-speakers", default=20, help="Max speakers for diarization")
@click.option("--vocabulary", type=click.Path(exists=True, path_type=Path), help="Custom vocabulary file")
@click.option("--domain", type=click.Choice(["medical", "legal", "military"]), help="Domain preset")
@click.option("--device", default="auto", help="Device: auto, cpu, cuda")
def transcribe(
    audio_file: Path,
    output: Optional[Path],
    fmt: str,
    model: str,
    language: Optional[str],
    diarize: bool,
    min_speakers: int,
    max_speakers: int,
    vocabulary: Optional[Path],
    domain: Optional[str],
    device: str,
) -> None:
    """Transcribe an audio file."""
    from .transcriber import Transcriber
    from .formatters import format_output

    with console.status("[bold green]Loading model..."):
        transcriber = Transcriber(model_size=model, device=device)

    if vocabulary or domain:
        transcriber.set_vocabulary(vocabulary_file=vocabulary, domain=domain)

    with console.status("[bold green]Transcribing..."):
        result = transcriber.transcribe(audio_file, language=language)

    if diarize:
        with console.status("[bold green]Diarizing speakers..."):
            from .diarization import DiarizationPipeline
            pipeline = DiarizationPipeline()
            turns = pipeline.diarize(audio_file, min_speakers=min_speakers, max_speakers=max_speakers)
            result = pipeline.assign_speakers(result, turns)

    formatted = format_output(result, fmt)

    if output:
        output.write_text(formatted, encoding="utf-8")
        console.print(f"[green]✓[/green] Saved to {output}")
    else:
        click.echo(formatted)


@main.command()
@click.argument("input_dir", type=click.Path(exists=True, path_type=Path))
@click.option("--output", "-o", type=click.Path(path_type=Path), default="./transcripts", help="Output directory")
@click.option("--format", "-f", "fmt", default="txt", help="Output format")
@click.option("--model", "-m", default="large-v3", help="Whisper model size")
@click.option("--diarize", is_flag=True, help="Enable speaker diarization")
@click.option("--vocabulary", type=click.Path(exists=True, path_type=Path), help="Custom vocabulary file")
@click.option("--domain", type=click.Choice(["medical", "legal", "military"]), help="Domain preset")
@click.option("--device", default="auto", help="Device: auto, cpu, cuda")
def batch(
    input_dir: Path,
    output: Path,
    fmt: str,
    model: str,
    diarize: bool,
    vocabulary: Optional[Path],
    domain: Optional[str],
    device: str,
) -> None:
    """Batch transcribe all audio files in a directory."""
    from .transcriber import Transcriber
    from .formatters import format_output

    AUDIO_EXTENSIONS = {".mp3", ".wav", ".flac", ".ogg", ".m4a", ".wma", ".aac", ".opus"}
    audio_files = sorted(f for f in input_dir.iterdir() if f.suffix.lower() in AUDIO_EXTENSIONS)

    if not audio_files:
        console.print("[red]No audio files found[/red]")
        sys.exit(1)

    output.mkdir(parents=True, exist_ok=True)

    with console.status("[bold green]Loading model..."):
        transcriber = Transcriber(model_size=model, device=device)

    if vocabulary or domain:
        transcriber.set_vocabulary(vocabulary_file=vocabulary, domain=domain)

    diarization_pipeline = None
    if diarize:
        from .diarization import DiarizationPipeline
        diarization_pipeline = DiarizationPipeline()

    with Progress() as progress:
        task = progress.add_task("Transcribing...", total=len(audio_files))
        for audio_file in audio_files:
            result = transcriber.transcribe(audio_file)
            if diarization_pipeline:
                turns = diarization_pipeline.diarize(audio_file)
                result = diarization_pipeline.assign_speakers(result, turns)

            formatted = format_output(result, fmt)
            ext_map = {"json": ".json", "srt": ".srt", "vtt": ".vtt", "md": ".md", "markdown": ".md"}
            ext = ext_map.get(fmt, ".txt")
            out_file = output / f"{audio_file.stem}{ext}"
            out_file.write_text(formatted, encoding="utf-8")
            progress.advance(task)

    console.print(f"[green]✓[/green] Transcribed {len(audio_files)} files to {output}")


@main.command()
@click.option("--host", default="0.0.0.0", help="Bind host")
@click.option("--port", "-p", default=8080, help="Bind port")
@click.option("--model", "-m", default="large-v3", help="Whisper model size")
@click.option("--device", default="auto", help="Device: auto, cpu, cuda")
def serve(host: str, port: int, model: str, device: str) -> None:
    """Start the REST API server."""
    import uvicorn
    import os
    os.environ.setdefault("AIRSCRIBE_MODEL", model)
    os.environ.setdefault("AIRSCRIBE_DEVICE", device)
    uvicorn.run("airscribe.api:app", host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
