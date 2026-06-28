"""Custom exceptions for the audio_prep pipeline.

Keeping these distinct from builtin exceptions makes it easy for callers
(and tests) to distinguish "ffmpeg/ffprobe failed" from generic bugs.
"""

from __future__ import annotations


class AudioPrepError(Exception):
    """Base class for all audio_prep errors."""


class ConversionError(AudioPrepError):
    """Raised when ffmpeg fails to convert a source file."""

    def __init__(self, source: str, returncode: int, stderr: str) -> None:
        self.source = source
        self.returncode = returncode
        self.stderr = stderr
        super().__init__(
            f"ffmpeg failed converting {source!r} (exit code {returncode}): {stderr.strip()}"
        )


class ProbeError(AudioPrepError):
    """Raised when ffprobe fails to read metadata from a file."""

    def __init__(self, source: str, reason: str) -> None:
        self.source = source
        self.reason = reason
        super().__init__(f"ffprobe failed reading {source!r}: {reason}")
