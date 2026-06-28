from __future__ import annotations

import json
from pathlib import Path

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
    import pytest

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
