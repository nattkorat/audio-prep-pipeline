from __future__ import annotations

from pathlib import Path

import pytest
import soundfile as sf

from audio_prep import converter
from audio_prep.config import ConversionConfig
from audio_prep.converter import _build_ffmpeg_cmd, convert_batch, convert_file, find_audio_files
from tests.conftest import make_sine_audio, make_sine_mp3


class TestFindAudioFiles:
    def test_finds_supported_source_files_recursively(self, source_corpus: Path) -> None:
        files = find_audio_files(source_corpus)
        names = {f.name for f in files}
        assert "clip_001.mp3" in names
        assert "broken.mp3" in names  # discovery doesn't validate, just lists
        assert "notes.txt" not in names

    def test_finds_common_ffmpeg_audio_containers_by_default(self, tmp_path: Path) -> None:
        input_dir = tmp_path / "raw"
        make_sine_audio(input_dir / "clip.wav", duration=1.0)
        make_sine_audio(input_dir / "clip.flac", duration=1.0)
        make_sine_audio(input_dir / "clip.m4a", duration=1.0)
        (input_dir / "notes.txt").write_text("not audio")

        files = find_audio_files(input_dir)

        assert [p.name for p in files] == ["clip.flac", "clip.m4a", "clip.wav"]

    def test_accepts_custom_extension_filter_without_leading_dot(self, tmp_path: Path) -> None:
        input_dir = tmp_path / "raw"
        make_sine_audio(input_dir / "clip.wav", duration=1.0)
        make_sine_mp3(input_dir / "clip.mp3", duration=1.0)

        files = find_audio_files(input_dir, extensions=("wav",))

        assert [p.name for p in files] == ["clip.wav"]

    def test_extensions_none_returns_every_regular_file(self, tmp_path: Path) -> None:
        input_dir = tmp_path / "raw"
        make_sine_audio(input_dir / "clip.wav", duration=1.0)
        (input_dir / "notes.txt").write_text("not audio")

        files = find_audio_files(input_dir, extensions=None)

        assert [p.name for p in files] == ["clip.wav", "notes.txt"]

    def test_returns_sorted_deterministic_order(self, source_corpus: Path) -> None:
        files = find_audio_files(source_corpus)
        assert files == sorted(files)

    def test_raises_on_missing_directory(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            find_audio_files(tmp_path / "does_not_exist")

    def test_empty_directory_returns_empty_list(self, tmp_path: Path) -> None:
        empty = tmp_path / "empty"
        empty.mkdir()
        assert find_audio_files(empty) == []


class TestConvertFile:
    def test_converts_to_requested_sample_rate_and_channels(
        self, sine_mp3: Path, tmp_path: Path, default_config: ConversionConfig
    ) -> None:
        dest = tmp_path / "out.wav"
        result = convert_file(sine_mp3, dest, default_config)

        assert result.success
        assert dest.is_file()
        info = sf.info(str(dest))
        assert info.samplerate == default_config.sample_rate
        assert info.channels == default_config.channels

    def test_converts_to_flac(self, sine_mp3: Path, tmp_path: Path) -> None:
        config = ConversionConfig(output_format="flac", sample_rate=16_000, channels=1)
        dest = tmp_path / "out.flac"
        result = convert_file(sine_mp3, dest, config)

        assert result.success
        assert dest.suffix == ".flac"
        info = sf.info(str(dest))
        assert info.format == "FLAC"

    def test_converts_non_mp3_source(
        self, tmp_path: Path, default_config: ConversionConfig
    ) -> None:
        source = make_sine_audio(tmp_path / "source.m4a", duration=1.0)
        dest = tmp_path / "out.wav"

        result = convert_file(source, dest, default_config)

        assert result.success
        assert dest.is_file()
        assert sf.info(str(dest)).samplerate == default_config.sample_rate

    def test_preserves_approximate_duration(
        self, tmp_path: Path, default_config: ConversionConfig
    ) -> None:
        src = make_sine_mp3(tmp_path / "two_sec.mp3", duration=2.0)
        dest = tmp_path / "two_sec.wav"
        convert_file(src, dest, default_config)

        info = sf.info(str(dest))
        duration = info.frames / info.samplerate
        assert duration == pytest.approx(2.0, abs=0.2)

    def test_missing_source_returns_failure_not_exception(
        self, tmp_path: Path, default_config: ConversionConfig
    ) -> None:
        result = convert_file(tmp_path / "nope.mp3", tmp_path / "out.wav", default_config)
        assert not result.success
        assert result.output is None
        assert "not found" in (result.error or "")

    def test_corrupt_source_returns_failure_not_exception(
        self, corrupt_mp3: Path, tmp_path: Path, default_config: ConversionConfig
    ) -> None:
        result = convert_file(corrupt_mp3, tmp_path / "out.wav", default_config)
        assert not result.success
        assert result.error is not None

    def test_skips_existing_valid_output_when_not_overwriting(
        self,
        sine_mp3: Path,
        tmp_path: Path,
        default_config: ConversionConfig,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        dest = tmp_path / "out.wav"
        initial = convert_file(sine_mp3, dest, default_config)
        assert initial.success
        original_bytes = dest.read_bytes()

        def fail_if_ffmpeg_runs(*args: object, **kwargs: object) -> None:
            pytest.fail("ffmpeg should not run for an existing valid output")

        monkeypatch.setattr(converter.subprocess, "run", fail_if_ffmpeg_runs)

        result = convert_file(sine_mp3, dest, default_config)

        assert result.success
        assert dest.read_bytes() == original_bytes

    def test_rewrites_corrupt_existing_output_when_not_overwriting(
        self, sine_mp3: Path, tmp_path: Path, default_config: ConversionConfig
    ) -> None:
        dest = tmp_path / "out.wav"
        dest.write_bytes(b"already here, but not actually audio")

        result = convert_file(sine_mp3, dest, default_config)

        assert result.success
        info = sf.info(str(dest))
        assert info.samplerate == default_config.sample_rate
        assert info.channels == default_config.channels

    def test_rewrites_existing_output_with_wrong_spec_when_not_overwriting(
        self, sine_mp3: Path, tmp_path: Path, default_config: ConversionConfig
    ) -> None:
        dest = tmp_path / "out.wav"
        wrong_config = ConversionConfig(sample_rate=8_000, channels=1, overwrite=True)
        initial = convert_file(sine_mp3, dest, wrong_config)
        assert initial.success
        assert sf.info(str(dest)).samplerate == 8_000

        result = convert_file(sine_mp3, dest, default_config)

        assert result.success
        assert sf.info(str(dest)).samplerate == default_config.sample_rate

    def test_invalid_existing_output_that_cannot_be_replaced_returns_failure(
        self, sine_mp3: Path, tmp_path: Path, default_config: ConversionConfig
    ) -> None:
        dest = tmp_path / "out.wav"
        dest.mkdir()

        result = convert_file(sine_mp3, dest, default_config)

        assert not result.success
        assert result.output is None
        assert "could not replace invalid existing output" in (result.error or "")

    def test_overwrite_true_replaces_existing_output(self, sine_mp3: Path, tmp_path: Path) -> None:
        config = ConversionConfig(sample_rate=16_000, channels=1, overwrite=True)
        dest = tmp_path / "out.wav"
        dest.write_bytes(b"stale placeholder")

        result = convert_file(sine_mp3, dest, config)

        assert result.success
        assert dest.read_bytes() != b"stale placeholder"

    def test_creates_nested_output_directories(
        self, sine_mp3: Path, tmp_path: Path, default_config: ConversionConfig
    ) -> None:
        dest = tmp_path / "a" / "b" / "c" / "out.wav"
        result = convert_file(sine_mp3, dest, default_config)
        assert result.success
        assert dest.is_file()

    def test_missing_ffmpeg_binary_returns_failure_not_exception(
        self,
        sine_mp3: Path,
        tmp_path: Path,
        default_config: ConversionConfig,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        def no_ffmpeg(*args: object, **kwargs: object) -> None:
            raise FileNotFoundError("No such file or directory: 'ffmpeg'")

        monkeypatch.setattr(converter.subprocess, "run", no_ffmpeg)

        result = convert_file(sine_mp3, tmp_path / "out.wav", default_config)

        assert not result.success
        assert result.output is None
        assert "ffmpeg" in (result.error or "")


class TestBuildFfmpegCmd:
    def test_normalize_loudness_adds_loudnorm_filter(self, tmp_path: Path) -> None:
        config = ConversionConfig(sample_rate=16_000, channels=1, normalize_loudness=True)
        cmd = _build_ffmpeg_cmd(tmp_path / "in.mp3", tmp_path / "out.wav", config)
        assert "-af" in cmd
        assert any("loudnorm" in part for part in cmd)

    def test_default_config_omits_loudnorm_filter(self, tmp_path: Path) -> None:
        config = ConversionConfig(sample_rate=16_000, channels=1)
        cmd = _build_ffmpeg_cmd(tmp_path / "in.mp3", tmp_path / "out.wav", config)
        assert "-af" not in cmd

    def test_normalize_loudness_converts_successfully_end_to_end(
        self, sine_mp3: Path, tmp_path: Path
    ) -> None:
        config = ConversionConfig(
            sample_rate=16_000, channels=1, normalize_loudness=True, overwrite=True
        )
        result = convert_file(sine_mp3, tmp_path / "out.wav", config)
        assert result.success
        assert result.output is not None and result.output.is_file()


class TestConvertBatch:
    def test_converts_all_valid_files_and_reports_failures(
        self, source_corpus: Path, tmp_path: Path
    ) -> None:
        output_dir = tmp_path / "out"
        config = ConversionConfig(sample_rate=16_000, channels=1, num_workers=1)

        results = convert_batch(source_corpus, output_dir, config)

        assert len(results) == 5  # 4 mp3-named files incl. broken + too_short
        failures = [r for r in results if not r.success]
        successes = [r for r in results if r.success]
        assert len(failures) == 1  # only the corrupt file fails at conversion time
        assert failures[0].source.name == "broken.mp3"
        assert len(successes) == 4

    def test_mirrors_input_subdirectory_structure(
        self, source_corpus: Path, tmp_path: Path
    ) -> None:
        output_dir = tmp_path / "out"
        config = ConversionConfig(sample_rate=16_000, channels=1, num_workers=1)

        results = convert_batch(source_corpus, output_dir, config)
        ok = next(
            r
            for r in results
            if r.success and r.source.name == "clip_001.mp3" and "speaker_a" in str(r.source)
        )
        assert ok.output is not None
        assert ok.output.parent.name == "speaker_a"

    def test_parallel_and_sequential_workers_produce_same_results(
        self, source_corpus: Path, tmp_path: Path
    ) -> None:
        config_seq = ConversionConfig(sample_rate=16_000, channels=1, num_workers=1)
        config_par = ConversionConfig(sample_rate=16_000, channels=1, num_workers=4)

        results_seq = convert_batch(source_corpus, tmp_path / "seq", config_seq)
        results_par = convert_batch(source_corpus, tmp_path / "par", config_par)

        seq_sources = [r.source.name for r in results_seq]
        par_sources = [r.source.name for r in results_par]
        assert seq_sources == par_sources  # deterministic ordering regardless of worker count

    def test_empty_input_directory_returns_empty_results(
        self, tmp_path: Path, default_config: ConversionConfig
    ) -> None:
        empty_input = tmp_path / "empty"
        empty_input.mkdir()
        results = convert_batch(empty_input, tmp_path / "out", default_config)
        assert results == []

    def test_default_discovery_converts_mixed_source_formats(self, tmp_path: Path) -> None:
        input_dir = tmp_path / "raw"
        make_sine_mp3(input_dir / "a.mp3", duration=1.0)
        make_sine_audio(input_dir / "b.wav", duration=1.0)
        (input_dir / "notes.txt").write_text("not audio")
        config = ConversionConfig(sample_rate=16_000, channels=1, num_workers=1)

        results = convert_batch(input_dir, tmp_path / "out", config)

        assert [r.source.name for r in results] == ["a.mp3", "b.wav"]
        assert all(r.success for r in results)

    def test_same_stem_different_source_formats_do_not_collide(self, tmp_path: Path) -> None:
        input_dir = tmp_path / "raw"
        make_sine_mp3(input_dir / "clip.mp3", duration=1.0)
        make_sine_audio(input_dir / "clip.wav", duration=1.0)
        config = ConversionConfig(sample_rate=16_000, channels=1, num_workers=1)

        results = convert_batch(input_dir, tmp_path / "out", config)

        outputs = sorted(r.output.name for r in results if r.output is not None)
        assert outputs == ["clip_mp3.wav", "clip_wav.wav"]
        assert all(r.success for r in results)
