"""Tests for audio_prep.chunker.

Silero VAD (torch + silero-vad) is an optional extra, so these tests
never load a real model: `chunk_audio_with_vad`/`chunk_file` accept a
`detect` callable, and `chunk_batch` is exercised via a monkeypatched
`load_vad_model`, so the VAD stage itself is a fake, deterministic
"which samples are speech" function.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from audio_prep import chunker
from audio_prep.chunker import (
    ChunkConfig,
    chunk_audio_with_vad,
    chunk_batch,
    chunk_file,
)

SR = 16_000


def make_sine_wav(path: Path, duration: float, frequency: int = 440, sr: int = SR) -> Path:
    """Write a synthetic sine-wave WAV directly via soundfile (no ffmpeg needed)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    audio = 0.5 * np.sin(2 * np.pi * frequency * t).astype(np.float32)
    sf.write(str(path), audio, sr)
    return path


def all_speech_detect(audio: np.ndarray, sampling_rate: int) -> list[dict[str, int]]:
    """Fake VAD: the entire clip is one speech segment."""
    return [{"start": 0, "end": len(audio)}]


def no_speech_detect(audio: np.ndarray, sampling_rate: int) -> list[dict[str, int]]:
    return []


class TestChunkConfig:
    """Tests for ChunkConfig validation."""

    def test_rejects_bad_output_format(self) -> None:
        with pytest.raises(ValueError, match="output_format"):
            ChunkConfig(output_format="mp3")

    def test_rejects_max_below_min(self) -> None:
        with pytest.raises(ValueError, match="max_duration_sec"):
            ChunkConfig(min_duration_sec=10, max_duration_sec=5)

    def test_rejects_non_positive_workers(self) -> None:
        with pytest.raises(ValueError, match="num_workers"):
            ChunkConfig(num_workers=0)

    def test_rejects_non_positive_sample_rate(self) -> None:
        with pytest.raises(ValueError, match="sample_rate"):
            ChunkConfig(sample_rate=0)

    def test_rejects_non_positive_min_duration(self) -> None:
        with pytest.raises(ValueError, match="min_duration_sec"):
            ChunkConfig(min_duration_sec=0)


class TestEnergyDetector:
    """_energy_based_detector: the offline RMS fallback VAD."""

    def test_detects_loud_region_between_silence(self) -> None:
        audio = np.zeros(SR * 3, dtype=np.float32)
        audio[SR : 2 * SR] = 0.5  # 1s of "speech" between 1s silence either side

        timestamps = chunker._energy_based_detector(audio, SR)

        assert len(timestamps) == 1
        # SR is a multiple of the 20ms frame size, so boundaries land exactly
        assert timestamps[0] == {"start": SR, "end": 2 * SR}

    def test_trailing_speech_extends_to_end_of_audio(self) -> None:
        audio = np.zeros(SR * 2, dtype=np.float32)
        audio[SR:] = 0.5  # speech runs right up to the last sample

        timestamps = chunker._energy_based_detector(audio, SR)

        assert timestamps
        assert timestamps[-1]["end"] == len(audio)

    def test_audio_shorter_than_one_frame_returns_empty(self) -> None:
        assert chunker._energy_based_detector(np.zeros(10, dtype=np.float32), SR) == []

    def test_audio_of_exactly_one_frame_returns_empty(self) -> None:
        one_frame = np.zeros(int(0.02 * SR), dtype=np.float32)
        assert chunker._energy_based_detector(one_frame, SR) == []


class TestLoadVadModel:
    """Loader fallback + caching, with the real Silero loaders stubbed out."""

    @pytest.fixture(autouse=True)
    def clear_cache(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(chunker, "_vad_model_cache", None)
        monkeypatch.setattr(chunker, "_vad_detector_cache", None)

    @pytest.fixture
    def broken_loaders(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def boom() -> tuple[object, object]:
            raise RuntimeError("silero unavailable")

        monkeypatch.setattr(chunker, "_load_vad_from_package", boom)
        monkeypatch.setattr(chunker, "_load_vad_from_torch_hub", boom)

    def test_raises_when_silero_unavailable_and_fallback_disabled(
        self, broken_loaders: None
    ) -> None:
        with pytest.raises(chunker.ChunkingError, match="allow_energy_fallback"):
            chunker.load_vad_model(allow_energy_fallback=False)

    def test_falls_back_to_energy_detector_when_allowed(self, broken_loaders: None) -> None:
        model, detect = chunker.load_vad_model(allow_energy_fallback=True)
        assert model is None
        assert detect is chunker._energy_based_detector

    def test_uses_first_working_loader_and_caches_result(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        sentinel = object()
        monkeypatch.setattr(
            chunker, "_load_vad_from_package", lambda: (sentinel, all_speech_detect)
        )

        model, detect = chunker.load_vad_model()
        assert model is sentinel
        assert detect is all_speech_detect

        # A second call must return the cached pair, not re-invoke a loader.
        monkeypatch.setattr(
            chunker,
            "_load_vad_from_package",
            lambda: pytest.fail("loader re-invoked despite warm cache"),
        )
        model_again, detect_again = chunker.load_vad_model()
        assert model_again is sentinel
        assert detect_again is all_speech_detect


class TestChunkAudioWithVad:
    def test_splits_long_speech_into_max_duration_windows(self) -> None:
        audio = np.zeros(SR * 9, dtype=np.float32)  # 9s of "speech"
        config = ChunkConfig(min_duration_sec=1, max_duration_sec=4)

        chunks = chunk_audio_with_vad(audio, SR, config, detect=all_speech_detect)

        assert [c["duration"] for c in chunks] == pytest.approx([4.0, 4.0, 1.0])
        # chunks tile the source without gaps or overlap
        assert chunks[0]["start"] == 0
        assert chunks[-1]["end"] == len(audio)

    def test_drops_leftover_shorter_than_min_duration(self) -> None:
        audio = np.zeros(SR * 4, dtype=np.float32)  # 4s of "speech"
        config = ChunkConfig(min_duration_sec=3, max_duration_sec=3)

        chunks = chunk_audio_with_vad(audio, SR, config, detect=all_speech_detect)

        # one 3s chunk; the trailing 1s remainder is below min_duration and dropped
        assert len(chunks) == 1
        assert chunks[0]["duration"] == pytest.approx(3.0)

    def test_no_speech_returns_no_chunks(self) -> None:
        audio = np.zeros(SR * 5, dtype=np.float32)
        chunks = chunk_audio_with_vad(audio, SR, ChunkConfig(), detect=no_speech_detect)
        assert chunks == []

    def test_downmixes_multichannel_audio(self) -> None:
        stereo = np.zeros((SR * 2, 2), dtype=np.float32)
        config = ChunkConfig(min_duration_sec=1, max_duration_sec=2)
        chunks = chunk_audio_with_vad(stereo, SR, config, detect=all_speech_detect)
        assert chunks[0]["audio"].ndim == 1


class TestChunkFile:
    def test_writes_expected_number_of_chunk_files(self, tmp_path: Path) -> None:
        source = make_sine_wav(tmp_path / "in" / "clip.wav", duration=9.0)
        output_dir = tmp_path / "out"
        config = ChunkConfig(min_duration_sec=1, max_duration_sec=4)

        result = chunk_file(source, output_dir, config, detect=all_speech_detect)

        assert result.success
        assert len(result.chunks) == 3
        assert [p.name for p in result.chunks] == [
            "clip_chunk_1.wav",
            "clip_chunk_2.wav",
            "clip_chunk_3.wav",
        ]
        for p in result.chunks:
            assert p.is_file()
            info = sf.info(str(p))
            assert info.samplerate == SR

    def test_writes_flac_when_configured(self, tmp_path: Path) -> None:
        source = make_sine_wav(tmp_path / "clip.wav", duration=2.0)
        config = ChunkConfig(min_duration_sec=1, max_duration_sec=2, output_format="flac")

        result = chunk_file(source, tmp_path / "out", config, detect=all_speech_detect)

        assert result.success
        assert result.chunks[0].suffix == ".flac"
        assert sf.info(str(result.chunks[0])).format == "FLAC"

    def test_no_speech_is_a_failure_not_an_exception(self, tmp_path: Path) -> None:
        source = make_sine_wav(tmp_path / "clip.wav", duration=2.0)
        result = chunk_file(source, tmp_path / "out", ChunkConfig(), detect=no_speech_detect)
        assert not result.success
        assert result.chunks == []
        assert "no speech" in (result.error or "")

    def test_missing_source_returns_failure_not_exception(self, tmp_path: Path) -> None:
        result = chunk_file(
            tmp_path / "nope.wav", tmp_path / "out", ChunkConfig(), detect=all_speech_detect
        )
        assert not result.success
        assert "not found" in (result.error or "")

    def test_unreadable_source_returns_failure_not_exception(
        self, corrupt_mp3: Path, tmp_path: Path
    ) -> None:
        result = chunk_file(corrupt_mp3, tmp_path / "out", ChunkConfig(), detect=all_speech_detect)
        assert not result.success
        assert result.chunks == []
        assert "could not read" in (result.error or "")

    def test_vad_load_failure_returns_failure_not_exception(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        source = make_sine_wav(tmp_path / "clip.wav", duration=2.0)

        def raise_chunking_error(allow_energy_fallback: bool = False) -> tuple[object, object]:
            raise chunker.ChunkingError("<vad model>", "no model available")

        monkeypatch.setattr(chunker, "load_vad_model", raise_chunking_error)

        # detect=None forces chunk_audio_with_vad to go through load_vad_model
        result = chunk_file(source, tmp_path / "out", ChunkConfig(), detect=None)

        assert not result.success
        assert "no model available" in (result.error or "")

    def test_rewrites_corrupt_existing_chunk_even_without_overwrite(self, tmp_path: Path) -> None:
        source = make_sine_wav(tmp_path / "clip.wav", duration=2.0)
        output_dir = tmp_path / "out"
        config = ChunkConfig(min_duration_sec=1, max_duration_sec=2)

        chunk_file(source, output_dir, config, detect=all_speech_detect)
        existing = output_dir / "clip_chunk_1.wav"
        existing.write_bytes(b"garbage, not audio")

        result = chunk_file(source, output_dir, config, detect=all_speech_detect)

        assert result.success
        info = sf.info(str(existing))  # readable audio again, not the garbage bytes
        assert info.frames > 0
        assert info.samplerate == SR

    def test_skips_existing_valid_chunk_when_not_overwriting(self, tmp_path: Path) -> None:
        source = make_sine_wav(tmp_path / "clip.wav", duration=2.0)
        output_dir = tmp_path / "out"
        config = ChunkConfig(min_duration_sec=1, max_duration_sec=2)

        chunk_file(source, output_dir, config, detect=all_speech_detect)
        existing = output_dir / "clip_chunk_1.wav"
        original_bytes = existing.read_bytes()
        existing.write_bytes(original_bytes)  # no-op, just to anchor the mtime/content check

        result = chunk_file(source, output_dir, config, detect=all_speech_detect)
        assert result.success
        assert existing.read_bytes() == original_bytes


class TestChunkFileResampling:
    """`config.sample_rate` resamples (via ffmpeg) before VAD + writing chunks."""

    def test_downsamples_when_sample_rate_differs(self, tmp_path: Path) -> None:
        source = make_sine_wav(tmp_path / "clip.wav", duration=2.0, sr=SR)  # native 16kHz
        config = ChunkConfig(min_duration_sec=1, max_duration_sec=2, sample_rate=8_000)

        result = chunk_file(source, tmp_path / "out", config, detect=all_speech_detect)

        assert result.success
        assert sf.info(str(result.chunks[0])).samplerate == 8_000

    def test_leaves_audio_untouched_when_already_at_target_rate(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        source = make_sine_wav(tmp_path / "clip.wav", duration=2.0, sr=SR)
        config = ChunkConfig(min_duration_sec=1, max_duration_sec=2, sample_rate=SR)

        def _boom(*args: object, **kwargs: object) -> None:
            raise AssertionError(
                "ffmpeg should not run when the source already matches sample_rate"
            )

        monkeypatch.setattr(chunker.subprocess, "run", _boom)

        result = chunk_file(source, tmp_path / "out", config, detect=all_speech_detect)

        assert result.success
        assert sf.info(str(result.chunks[0])).samplerate == SR

    def test_default_sample_rate_none_preserves_native_rate(self, tmp_path: Path) -> None:
        source = make_sine_wav(tmp_path / "clip.wav", duration=2.0, sr=8_000)
        config = ChunkConfig(min_duration_sec=1, max_duration_sec=2)  # sample_rate=None

        result = chunk_file(source, tmp_path / "out", config, detect=all_speech_detect)

        assert result.success
        assert sf.info(str(result.chunks[0])).samplerate == 8_000


class TestChunkFileMp3Source:
    """MP3 sources always decode via ffmpeg, regardless of `sample_rate`."""

    def test_chunks_mp3_source_at_native_rate(self, tmp_path: Path) -> None:
        from tests.conftest import make_sine_mp3

        source = make_sine_mp3(tmp_path / "clip.mp3", duration=3.0, sample_rate=44_100)
        config = ChunkConfig(min_duration_sec=1, max_duration_sec=3)  # sample_rate=None

        result = chunk_file(source, tmp_path / "out", config, detect=all_speech_detect)

        assert result.success
        assert sf.info(str(result.chunks[0])).samplerate == 44_100

    def test_resamples_mp3_source_to_requested_rate(self, tmp_path: Path) -> None:
        from tests.conftest import make_sine_mp3

        source = make_sine_mp3(tmp_path / "clip.mp3", duration=3.0, sample_rate=44_100)
        config = ChunkConfig(min_duration_sec=1, max_duration_sec=3, sample_rate=16_000)

        result = chunk_file(source, tmp_path / "out", config, detect=all_speech_detect)

        assert result.success
        assert sf.info(str(result.chunks[0])).samplerate == 16_000


class TestChunkBatch:
    @pytest.fixture(autouse=True)
    def fake_vad_model(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Bypass Silero entirely: chunk_batch/chunk_file resolve `detect`
        via `load_vad_model` when not called with an explicit override.
        """
        monkeypatch.setattr(
            chunker, "load_vad_model", lambda allow_energy_fallback=False: (None, all_speech_detect)
        )

    def test_mirrors_input_subdirectory_structure(self, tmp_path: Path) -> None:
        from tests.conftest import make_sine_mp3

        input_dir = tmp_path / "raw"
        make_sine_mp3(input_dir / "speaker_a" / "clip.mp3", duration=6.0)
        make_sine_mp3(input_dir / "speaker_b" / "clip.mp3", duration=6.0)
        output_dir = tmp_path / "chunks"
        config = ChunkConfig(min_duration_sec=1, max_duration_sec=3, num_workers=1)

        results = chunk_batch(input_dir, output_dir, config)

        assert len(results) == 2
        assert all(r.success for r in results)
        speaker_a_result = next(r for r in results if "speaker_a" in str(r.source))
        assert speaker_a_result.chunks[0].parent.name == "speaker_a"

    def test_empty_input_directory_returns_empty_results(self, tmp_path: Path) -> None:
        input_dir = tmp_path / "empty"
        input_dir.mkdir()
        results = chunk_batch(input_dir, tmp_path / "out", ChunkConfig())
        assert results == []

    def test_discovers_supported_non_mp3_files_by_default(self, tmp_path: Path) -> None:
        input_dir = tmp_path / "raw"
        make_sine_wav(input_dir / "scanned.wav", duration=3.0)
        results = chunk_batch(
            input_dir,
            tmp_path / "out",
            ChunkConfig(min_duration_sec=1, max_duration_sec=3),
        )
        assert len(results) == 1
        assert results[0].success

    def test_same_stem_different_source_formats_do_not_collide(self, tmp_path: Path) -> None:
        from tests.conftest import make_sine_mp3

        input_dir = tmp_path / "raw"
        make_sine_mp3(input_dir / "clip.mp3", duration=3.0)
        make_sine_wav(input_dir / "clip.wav", duration=3.0)
        output_dir = tmp_path / "out"
        config = ChunkConfig(min_duration_sec=1, max_duration_sec=3)

        results = chunk_batch(input_dir, output_dir, config)

        assert len(results) == 2
        assert all(r.success for r in results)
        assert (output_dir / "clip_mp3" / "clip_chunk_1.wav").exists()
        assert (output_dir / "clip_wav" / "clip_chunk_1.wav").exists()

    def test_accepts_preselected_source_files(self, tmp_path: Path) -> None:
        input_dir = tmp_path / "converted"
        keep = make_sine_wav(input_dir / "keep.wav", duration=3.0)
        make_sine_wav(input_dir / "skip.wav", duration=3.0)  # not passed in source_files
        config = ChunkConfig(min_duration_sec=1, max_duration_sec=3)

        results = chunk_batch(input_dir, tmp_path / "out", config, source_files=[keep])

        assert len(results) == 1
        assert results[0].source == keep
