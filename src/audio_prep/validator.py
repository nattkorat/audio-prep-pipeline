"""Post-conversion validation: catch silently-broken or out-of-spec output.

ffmpeg can exit 0 while still producing a near-empty or truncated file
(e.g. a corrupt source it half-decoded), so we re-check the *output*
independently rather than trusting the converter's success flag alone.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

import soundfile as sf

from audio_prep.config import ConversionConfig
from audio_prep.exceptions import ProbeError


@dataclass(slots=True)
class ValidationResult:
    """Outcome of validating a single converted file."""

    path: Path
    valid: bool
    duration_sec: float | None = None
    sample_rate: int | None = None
    channels: int | None = None
    reason: str | None = None


def probe_duration(path: Path) -> float:
    """Return duration in seconds via ffprobe.

    Works on any container ffmpeg understands, including the original
    MP3 source -- unlike soundfile, which only needs to handle our own
    WAV/FLAC output.
    """
    path = Path(path)
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise ProbeError(str(path), proc.stderr.strip())

    try:
        return float(proc.stdout.strip())
    except ValueError as exc:
        raise ProbeError(
            str(path), f"could not parse duration from output: {proc.stdout!r}"
        ) from exc


def validate_output(path: Path, config: ConversionConfig) -> ValidationResult:
    """Check a converted file matches the requested spec and isn't degenerate.

    Checks, in order: existence, non-zero size, readable header (soundfile),
    sample rate, channel count, minimum duration.
    """
    path = Path(path)

    if not path.is_file():
        return ValidationResult(path, valid=False, reason="file does not exist")

    if path.stat().st_size == 0:
        return ValidationResult(path, valid=False, reason="file is empty")

    try:
        info = sf.info(str(path))
    except Exception as exc:  # noqa: BLE001 - surface any backend decode failure as invalid
        return ValidationResult(path, valid=False, reason=f"unreadable audio file: {exc}")

    duration = info.frames / info.samplerate if info.samplerate else 0.0

    if info.samplerate != config.sample_rate:
        return ValidationResult(
            path,
            valid=False,
            duration_sec=duration,
            sample_rate=info.samplerate,
            channels=info.channels,
            reason=f"sample rate mismatch: expected {config.sample_rate}, got {info.samplerate}",
        )

    if info.channels != config.channels:
        return ValidationResult(
            path,
            valid=False,
            duration_sec=duration,
            sample_rate=info.samplerate,
            channels=info.channels,
            reason=f"channel count mismatch: expected {config.channels}, got {info.channels}",
        )

    if duration < config.min_duration_sec:
        return ValidationResult(
            path,
            valid=False,
            duration_sec=duration,
            sample_rate=info.samplerate,
            channels=info.channels,
            reason=f"duration {duration:.3f}s below minimum {config.min_duration_sec}s",
        )

    return ValidationResult(
        path,
        valid=True,
        duration_sec=duration,
        sample_rate=info.samplerate,
        channels=info.channels,
        reason=None,
    )
