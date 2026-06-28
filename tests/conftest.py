"""Shared pytest fixtures.

Test audio is generated on the fly with ffmpeg's `lavfi` sine-wave
source rather than checked into the repo as binary files. This keeps
the repo diff-friendly and means tests never go stale relative to
whatever ffmpeg build runs them.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from audio_prep.config import ConversionConfig


def make_sine_mp3(
    path: Path,
    duration: float = 1.0,
    frequency: int = 440,
    sample_rate: int = 44_100,
    channels: int = 1,
) -> Path:
    """Generate a synthetic sine-wave MP3 at ``path`` using ffmpeg lavfi."""
    path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"sine=frequency={frequency}:duration={duration}:sample_rate={sample_rate}",
        "-ac",
        str(channels),
        str(path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return path


def make_corrupt_file(path: Path) -> Path:
    """Write garbage bytes with an .mp3 extension to simulate a broken source file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"this is definitely not a valid mp3 stream \x00\x01\x02")
    return path


@pytest.fixture
def default_config() -> ConversionConfig:
    return ConversionConfig(output_format="wav", sample_rate=16_000, channels=1, num_workers=1)


@pytest.fixture
def sine_mp3(tmp_path: Path) -> Path:
    """A single valid 1-second synthetic MP3."""
    return make_sine_mp3(tmp_path / "sine.mp3", duration=1.0)


@pytest.fixture
def corrupt_mp3(tmp_path: Path) -> Path:
    """A file with an .mp3 extension that ffmpeg cannot decode."""
    return make_corrupt_file(tmp_path / "corrupt.mp3")


@pytest.fixture
def source_corpus(tmp_path: Path) -> Path:
    """A small input directory tree with several valid MP3s, a nested
    subfolder, one too-short clip, and one corrupt file -- enough to
    exercise discovery, batch conversion, and partial-failure handling.
    """
    input_dir = tmp_path / "raw_mp3"
    make_sine_mp3(input_dir / "speaker_a" / "clip_001.mp3", duration=2.0, frequency=220)
    make_sine_mp3(input_dir / "speaker_a" / "clip_002.mp3", duration=1.5, frequency=330)
    make_sine_mp3(input_dir / "speaker_b" / "clip_001.mp3", duration=3.0, frequency=440)
    make_sine_mp3(input_dir / "speaker_b" / "too_short.mp3", duration=0.1, frequency=440)
    make_corrupt_file(input_dir / "speaker_b" / "broken.mp3")
    # A non-audio file that discovery must ignore.
    (input_dir / "speaker_b" / "notes.txt").write_text("not audio")
    return input_dir
