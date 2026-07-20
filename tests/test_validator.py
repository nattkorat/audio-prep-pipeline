from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from audio_prep import validator
from audio_prep.config import ConversionConfig
from audio_prep.converter import convert_file
from audio_prep.exceptions import ProbeError
from audio_prep.validator import probe_duration, validate_output


class TestProbeDuration:
    def test_probes_mp3_duration_directly(self, sine_mp3: Path) -> None:
        duration = probe_duration(sine_mp3)
        assert duration == pytest.approx(1.0, abs=0.2)

    def test_raises_probe_error_on_nonexistent_file(self, tmp_path: Path) -> None:
        with pytest.raises(ProbeError):
            probe_duration(tmp_path / "nope.mp3")

    def test_raises_probe_error_on_corrupt_file(self, corrupt_mp3: Path) -> None:
        with pytest.raises(ProbeError):
            probe_duration(corrupt_mp3)

    def test_raises_probe_error_on_unparseable_ffprobe_output(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """ffprobe exiting 0 but printing a non-numeric duration must not crash."""
        fake = subprocess.CompletedProcess(args=[], returncode=0, stdout="N/A\n", stderr="")
        monkeypatch.setattr(validator.subprocess, "run", lambda *a, **kw: fake)

        with pytest.raises(ProbeError, match="could not parse duration"):
            probe_duration(tmp_path / "whatever.wav")


class TestValidateOutput:
    def test_valid_wav_passes(self, sine_mp3: Path, tmp_path: Path) -> None:
        config = ConversionConfig(sample_rate=16_000, channels=1, min_duration_sec=0.5)
        dest = tmp_path / "out.wav"
        convert_file(sine_mp3, dest, config)

        result = validate_output(dest, config)

        assert result.valid
        assert result.sample_rate == 16_000
        assert result.channels == 1
        assert result.duration_sec == pytest.approx(1.0, abs=0.2)
        assert result.reason is None

    def test_missing_file_is_invalid(
        self, tmp_path: Path, default_config: ConversionConfig
    ) -> None:
        result = validate_output(tmp_path / "nope.wav", default_config)
        assert not result.valid
        assert "does not exist" in (result.reason or "")

    def test_empty_file_is_invalid(self, tmp_path: Path, default_config: ConversionConfig) -> None:
        empty = tmp_path / "empty.wav"
        empty.touch()
        result = validate_output(empty, default_config)
        assert not result.valid
        assert "empty" in (result.reason or "")

    def test_sample_rate_mismatch_is_invalid(self, sine_mp3: Path, tmp_path: Path) -> None:
        write_config = ConversionConfig(sample_rate=44_100, channels=1)
        check_config = ConversionConfig(sample_rate=16_000, channels=1)
        dest = tmp_path / "out.wav"
        convert_file(sine_mp3, dest, write_config)

        result = validate_output(dest, check_config)

        assert not result.valid
        assert "sample rate mismatch" in (result.reason or "")

    def test_channel_mismatch_is_invalid(self, tmp_path: Path) -> None:
        from tests.conftest import make_sine_mp3

        src = make_sine_mp3(tmp_path / "stereo.mp3", duration=1.0, channels=2)
        write_config = ConversionConfig(sample_rate=16_000, channels=2)
        check_config = ConversionConfig(sample_rate=16_000, channels=1)
        dest = tmp_path / "out.wav"
        convert_file(src, dest, write_config)

        result = validate_output(dest, check_config)

        assert not result.valid
        assert "channel count mismatch" in (result.reason or "")

    def test_too_short_duration_is_invalid(self, tmp_path: Path) -> None:
        from tests.conftest import make_sine_mp3

        src = make_sine_mp3(tmp_path / "tiny.mp3", duration=0.1)
        config = ConversionConfig(sample_rate=16_000, channels=1, min_duration_sec=1.0)
        dest = tmp_path / "out.wav"
        convert_file(src, dest, config)

        result = validate_output(dest, config)

        assert not result.valid
        assert "below minimum" in (result.reason or "")

    def test_unreadable_file_is_invalid(
        self, tmp_path: Path, default_config: ConversionConfig
    ) -> None:
        fake = tmp_path / "out.wav"
        fake.write_bytes(b"not actually a wav file")
        result = validate_output(fake, default_config)
        assert not result.valid
        assert "unreadable" in (result.reason or "")
