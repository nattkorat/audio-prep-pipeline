from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from audio_prep.cli import main


def test_cli_convert_end_to_end_writes_manifest(source_corpus: Path, tmp_path: Path) -> None:
    output_dir = tmp_path / "out"
    manifest_path = tmp_path / "manifest.jsonl"

    exit_code = main(
        [
            "convert",
            "--input-dir",
            str(source_corpus),
            "--output-dir",
            str(output_dir),
            "--format",
            "wav",
            "--sample-rate",
            "16000",
            "--workers",
            "1",
            "--manifest",
            str(manifest_path),
        ]
    )

    # Non-zero because the corpus intentionally contains a broken + too-short file.
    assert exit_code == 1
    assert manifest_path.is_file()

    statuses = [json.loads(line)["status"] for line in manifest_path.read_text().splitlines()]
    assert statuses.count("ok") == 3
    assert statuses.count("conversion_failed") == 1
    assert statuses.count("validation_failed") == 1


def test_cli_convert_succeeds_cleanly_on_valid_only_input(tmp_path: Path) -> None:
    from tests.conftest import make_sine_mp3

    input_dir = tmp_path / "raw"
    make_sine_mp3(input_dir / "a.mp3", duration=1.0)
    make_sine_mp3(input_dir / "b.mp3", duration=1.0)

    exit_code = main(
        [
            "convert",
            "--input-dir",
            str(input_dir),
            "--output-dir",
            str(tmp_path / "out"),
            "--workers",
            "1",
        ]
    )

    assert exit_code == 0


def test_cli_rejects_unsupported_format(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        main(
            [
                "convert",
                "--input-dir",
                str(tmp_path),
                "--output-dir",
                str(tmp_path / "out"),
                "--format",
                "mp3",
            ]
        )


class TestCliChunk:
    @pytest.fixture(autouse=True)
    def fake_vad_model(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Bypass Silero entirely: `chunk` resolves `detect` via
        `load_vad_model`, which we replace with a fake "whole clip is
        speech" detector so this test never needs torch/silero-vad.
        """
        from audio_prep import chunker

        def all_speech_detect(audio: np.ndarray, sampling_rate: int) -> list[dict[str, int]]:
            return [{"start": 0, "end": len(audio)}]

        monkeypatch.setattr(
            chunker, "load_vad_model", lambda allow_energy_fallback=False: (None, all_speech_detect)
        )

    def test_chunk_command_writes_chunks_directly_from_mp3_dir(self, tmp_path: Path) -> None:
        from tests.conftest import make_sine_mp3

        input_dir = tmp_path / "raw"
        make_sine_mp3(input_dir / "clip.mp3", duration=9.0)

        exit_code = main(
            [
                "chunk",
                "--input-dir",
                str(input_dir),
                "--min-duration-sec",
                "1",
                "--max-duration-sec",
                "4",
            ]
        )

        assert exit_code == 0
        output_dir = input_dir / "chunks"
        chunks = sorted(output_dir.glob("clip_chunk_*.wav"))
        assert len(chunks) == 3

    def test_chunk_command_respects_custom_output_dir(self, tmp_path: Path) -> None:
        from tests.conftest import make_sine_mp3

        input_dir = tmp_path / "raw"
        make_sine_mp3(input_dir / "clip.mp3", duration=2.0)
        output_dir = tmp_path / "custom_chunks"

        exit_code = main(
            [
                "chunk",
                "--input-dir",
                str(input_dir),
                "--output-dir",
                str(output_dir),
                "--min-duration-sec",
                "1",
                "--max-duration-sec",
                "2",
            ]
        )

        assert exit_code == 0
        assert list(output_dir.glob("clip_chunk_*.wav"))

    def test_chunk_command_reports_failure_when_no_speech_detected(self, tmp_path: Path) -> None:
        from tests.conftest import make_sine_mp3

        input_dir = tmp_path / "raw"
        make_sine_mp3(input_dir / "silent.mp3", duration=1.0)

        exit_code = main(
            [
                "chunk",
                "--input-dir",
                str(input_dir),
                "--min-duration-sec",
                "5",
                "--max-duration-sec",
                "20",
            ]
        )

        # Clip is only 1s, below --min-duration-sec 5, so no chunks are produced.
        assert exit_code == 1

    def test_chunk_command_writes_manifest(self, tmp_path: Path) -> None:
        from tests.conftest import make_sine_mp3

        input_dir = tmp_path / "raw"
        make_sine_mp3(input_dir / "clip.mp3", duration=9.0)
        manifest_path = tmp_path / "chunk_manifest.jsonl"

        exit_code = main(
            [
                "chunk",
                "--input-dir",
                str(input_dir),
                "--min-duration-sec",
                "1",
                "--max-duration-sec",
                "4",
                "--manifest",
                str(manifest_path),
            ]
        )

        assert exit_code == 0
        assert manifest_path.is_file()
        record = json.loads(manifest_path.read_text().splitlines()[0])
        assert record["status"] == "ok"
        assert record["num_chunks"] == 3
