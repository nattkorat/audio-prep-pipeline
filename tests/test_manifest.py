from __future__ import annotations

import json
from pathlib import Path

from audio_prep.chunker import ChunkResult
from audio_prep.config import ConversionConfig
from audio_prep.converter import ConversionResult, convert_file
from audio_prep.manifest import build_chunk_manifest, build_manifest, write_manifest
from audio_prep.validator import validate_output


def test_build_manifest_marks_conversion_failures(tmp_path: Path) -> None:
    conversion_results = [
        ConversionResult(
            source=tmp_path / "broken.mp3", output=None, success=False, error="ffmpeg exploded"
        )
    ]
    records = build_manifest(conversion_results, validation_results={})

    assert len(records) == 1
    assert records[0].status == "conversion_failed"
    assert records[0].output_path is None
    assert records[0].error == "ffmpeg exploded"


def test_build_manifest_marks_validation_failures(tmp_path: Path) -> None:
    out = tmp_path / "out.wav"
    conversion_results = [ConversionResult(source=tmp_path / "src.mp3", output=out, success=True)]
    from audio_prep.validator import ValidationResult

    validations = {out: ValidationResult(path=out, valid=False, reason="sample rate mismatch")}

    records = build_manifest(conversion_results, validations)

    assert records[0].status == "validation_failed"
    assert records[0].error == "sample rate mismatch"


def test_build_manifest_marks_ok_records(sine_mp3: Path, tmp_path: Path) -> None:
    config = ConversionConfig(sample_rate=16_000, channels=1)
    dest = tmp_path / "out.wav"
    conv_result = convert_file(sine_mp3, dest, config)
    validation = validate_output(dest, config)

    records = build_manifest([conv_result], {dest: validation})

    assert records[0].status == "ok"
    assert records[0].sample_rate == 16_000
    assert records[0].duration_sec is not None
    assert records[0].error is None


def test_write_manifest_produces_valid_jsonl(sine_mp3: Path, tmp_path: Path) -> None:
    config = ConversionConfig(sample_rate=16_000, channels=1)
    dest = tmp_path / "out.wav"
    conv_result = convert_file(sine_mp3, dest, config)
    validation = validate_output(dest, config)
    records = build_manifest([conv_result], {dest: validation})

    manifest_path = tmp_path / "manifest.jsonl"
    write_manifest(records, manifest_path)

    lines = manifest_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    parsed = json.loads(lines[0])
    assert parsed["status"] == "ok"
    assert parsed["sample_rate"] == 16_000


def test_write_manifest_creates_parent_directories(tmp_path: Path) -> None:
    nested_path = tmp_path / "a" / "b" / "manifest.jsonl"
    write_manifest([], nested_path)
    assert nested_path.is_file()
    assert nested_path.read_text() == ""


def test_build_chunk_manifest_marks_success_and_failure(tmp_path: Path) -> None:
    ok_chunks = [tmp_path / "clip_chunk_1.wav", tmp_path / "clip_chunk_2.wav"]
    chunk_results = [
        ChunkResult(source=tmp_path / "clip.wav", chunks=ok_chunks, success=True),
        ChunkResult(
            source=tmp_path / "silent.wav",
            chunks=[],
            success=False,
            error="no speech chunks detected",
        ),
    ]

    records = build_chunk_manifest(chunk_results)

    assert records[0].status == "ok"
    assert records[0].num_chunks == 2
    assert records[0].chunk_paths == [str(p) for p in ok_chunks]
    assert records[0].error is None

    assert records[1].status == "chunking_failed"
    assert records[1].num_chunks == 0
    assert records[1].error == "no speech chunks detected"


def test_write_manifest_works_for_chunk_records(tmp_path: Path) -> None:
    chunk_results = [
        ChunkResult(
            source=tmp_path / "clip.wav", chunks=[tmp_path / "clip_chunk_1.wav"], success=True
        )
    ]
    records = build_chunk_manifest(chunk_results)

    manifest_path = tmp_path / "chunk_manifest.jsonl"
    write_manifest(records, manifest_path)

    lines = manifest_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    parsed = json.loads(lines[0])
    assert parsed["status"] == "ok"
    assert parsed["num_chunks"] == 1
