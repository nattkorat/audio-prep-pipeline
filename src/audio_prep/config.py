"""Pipeline configuration."""

from __future__ import annotations

from dataclasses import dataclass

SUPPORTED_OUTPUT_FORMATS = ("wav", "flac")


@dataclass(frozen=True, slots=True)
class ConversionConfig:
    """Target spec for converted audio + pipeline behavior knobs.

    Defaults (16 kHz, mono) match the standard input spec for
    Wav2Vec2 / XLS-R style speech pretraining.
    """

    output_format: str = "wav"
    sample_rate: int = 16_000
    channels: int = 1
    num_workers: int = 4
    min_duration_sec: float = 0.5
    overwrite: bool = False
    # ffmpeg loudness normalization (helps when source recordings vary wildly in level)
    normalize_loudness: bool = False

    def __post_init__(self) -> None:
        if self.output_format not in SUPPORTED_OUTPUT_FORMATS:
            raise ValueError(
                f"output_format must be one of {SUPPORTED_OUTPUT_FORMATS}, "
                f"got {self.output_format!r}"
            )
        if self.sample_rate <= 0:
            raise ValueError(f"sample_rate must be positive, got {self.sample_rate}")
        if self.channels <= 0:
            raise ValueError(f"channels must be positive, got {self.channels}")
        if self.num_workers <= 0:
            raise ValueError(f"num_workers must be positive, got {self.num_workers}")
        if self.min_duration_sec < 0:
            raise ValueError(f"min_duration_sec must be >= 0, got {self.min_duration_sec}")
