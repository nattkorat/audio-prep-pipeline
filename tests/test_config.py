from __future__ import annotations

import pytest

from audio_prep.config import ConversionConfig


def test_default_config_is_16khz_mono_wav() -> None:
    config = ConversionConfig()
    assert config.output_format == "wav"
    assert config.sample_rate == 16_000
    assert config.channels == 1


def test_accepts_flac_format() -> None:
    config = ConversionConfig(output_format="flac")
    assert config.output_format == "flac"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("output_format", "mp3"),
        ("sample_rate", 0),
        ("sample_rate", -16_000),
        ("channels", 0),
        ("num_workers", 0),
        ("num_workers", -1),
        ("min_duration_sec", -0.5),
    ],
)
def test_rejects_invalid_values(field: str, value: object) -> None:
    with pytest.raises(ValueError):
        ConversionConfig(**{field: value})


def test_config_is_immutable() -> None:
    config = ConversionConfig()
    with pytest.raises(AttributeError):
        config.sample_rate = 8_000  # type: ignore[misc]
