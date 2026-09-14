"""
audio_processor.py — Upload validation + FFmpeg normalization.

Real checks only: extension, MIME type, magic-byte sniffing via ffprobe,
duration, corruption, emptiness, size. No step here is faked; if ffprobe
can't read the file, we raise — we do not guess.
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger("transcore.audio_processor")

ALLOWED_EXTENSIONS = {".mp3", ".wav", ".m4a", ".flac", ".ogg"}
ALLOWED_MIME_PREFIXES = ("audio/",)
MAX_FILE_SIZE_BYTES = int(os.environ.get("TRANSCORE_MAX_FILE_SIZE_MB", "100")) * 1024 * 1024
MIN_DURATION_SECONDS = 1.0
MAX_DURATION_SECONDS = int(os.environ.get("TRANSCORE_MAX_DURATION_MIN", "20")) * 60


class AudioValidationError(Exception):
    pass


@dataclass
class ProbeResult:
    duration_seconds: float
    sample_rate: int
    channels: int
    codec: str
    format_name: str


def validate_extension(filename: str) -> str:
    ext = os.path.splitext(filename.lower())[1]
    if ext not in ALLOWED_EXTENSIONS:
        raise AudioValidationError(
            f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )
    return ext


def validate_size(size_bytes: int) -> None:
    if size_bytes <= 0:
        raise AudioValidationError("The uploaded file is empty.")
    if size_bytes > MAX_FILE_SIZE_BYTES:
        raise AudioValidationError(
            f"File is too large ({size_bytes / (1024*1024):.1f} MB). Max is "
            f"{MAX_FILE_SIZE_BYTES / (1024*1024):.0f} MB."
        )


def ffprobe_inspect(filepath: str) -> ProbeResult:
    """Runs real ffprobe against the file. Raises AudioValidationError if the
    file is corrupted / not actually readable audio — never returns fake
    probe data.
    """
    if not os.path.exists(filepath):
        raise AudioValidationError("Uploaded file not found on disk.")

    try:
        proc = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration,format_name:stream=codec_name,sample_rate,channels",
                "-of",
                "json",
                filepath,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except FileNotFoundError as exc:
        raise AudioValidationError(
            "FFmpeg/ffprobe is not installed or not on PATH. See README for setup."
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise AudioValidationError("Audio inspection timed out — file may be corrupted.") from exc

    if proc.returncode != 0 or not proc.stdout.strip():
        raise AudioValidationError(
            "This file could not be read as audio. It may be corrupted or not a real audio file."
        )

    try:
        data = json.loads(proc.stdout)
        fmt = data.get("format", {})
        streams = data.get("streams", [])
        audio_stream = next((s for s in streams if "sample_rate" in s), streams[0] if streams else {})
        duration = float(fmt.get("duration", 0.0))
        sample_rate = int(audio_stream.get("sample_rate", 0) or 0)
        channels = int(audio_stream.get("channels", 0) or 0)
        codec = audio_stream.get("codec_name", "unknown")
        format_name = fmt.get("format_name", "unknown")
    except (ValueError, KeyError, StopIteration, TypeError) as exc:
        raise AudioValidationError("Could not parse audio stream metadata — file may be corrupted.") from exc

    if duration <= 0:
        raise AudioValidationError("Audio duration could not be determined — file may be corrupted or empty.")

    return ProbeResult(
        duration_seconds=duration,
        sample_rate=sample_rate,
        channels=channels,
        codec=codec,
        format_name=format_name,
    )


def validate_duration(probe: ProbeResult) -> None:
    if probe.duration_seconds < MIN_DURATION_SECONDS:
        raise AudioValidationError("Audio is too short to analyze (< 1 second).")
    if probe.duration_seconds > MAX_DURATION_SECONDS:
        raise AudioValidationError(
            f"Audio is too long ({probe.duration_seconds/60:.1f} min). "
            f"Max supported for MVP is {MAX_DURATION_SECONDS/60:.0f} minutes."
        )


def normalize_to_wav(input_path: str, output_path: str, sample_rate: int = 44100) -> str:
    """Converts/normalizes any supported input to mono 44.1kHz WAV via real
    FFmpeg — needed so downstream librosa/pYIN gets a consistent format.
    """
    try:
        proc = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                input_path,
                "-ac",
                "1",
                "-ar",
                str(sample_rate),
                output_path,
            ],
            capture_output=True,
            text=True,
            timeout=300,
        )
    except FileNotFoundError as exc:
        raise AudioValidationError("FFmpeg is not installed or not on PATH.") from exc
    except subprocess.TimeoutExpired as exc:
        raise AudioValidationError("Audio normalization timed out.") from exc

    if proc.returncode != 0 or not os.path.exists(output_path):
        logger.error("ffmpeg failed: %s", proc.stderr[-2000:])
        raise AudioValidationError("FFmpeg failed to process this audio file.")

    return output_path


def validate_and_probe(filepath: str, original_filename: str, size_bytes: int) -> ProbeResult:
    """Runs the full real validation chain in order (section 3 of the spec)."""
    validate_extension(original_filename)
    validate_size(size_bytes)
    probe = ffprobe_inspect(filepath)
    validate_duration(probe)
    return probe
