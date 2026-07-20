"""Emit a JSONL manifest describing the converted dataset.

A manifest is the handoff artifact between this pipeline and the
pretraining code -- one JSON object per line so it streams cleanly
into HF `datasets`, fairseq dataset loaders, or a simple line-by-line
reader, without needing to load the whole file into memory.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, TypeVar

from audio_prep.chunker import ChunkResult
from audio_prep.converter import ConversionResult
from audio_prep.validator import ValidationResult

if TYPE_CHECKING:
    from _typeshed import DataclassInstance

_RecordT = TypeVar("_RecordT", bound="DataclassInstance")


@dataclass(slots=True)
class ManifestRecord:
    """One row of the output manifest."""

    source_path: str
    output_path: str | None
    status: str  # "ok" | "conversion_failed" | "validation_failed"
    duration_sec: float | None = None
    sample_rate: int | None = None
    channels: int | None = None
    error: str | None = None


@dataclass(slots=True)
class ChunkManifestRecord:
    """One row of the chunk-only manifest (from the standalone `chunk` command)."""

    source_path: str
    status: str  # "ok" | "chunking_failed"
    num_chunks: int = 0
    chunk_paths: list[str] = field(default_factory=list)
    error: str | None = None


def build_chunk_manifest(chunk_results: list[ChunkResult]) -> list[ChunkManifestRecord]:
    """Turn `chunk_batch` results into manifest records, one row per source file."""
    return [
        ChunkManifestRecord(
            source_path=str(result.source),
            status="ok" if result.success else "chunking_failed",
            num_chunks=len(result.chunks),
            chunk_paths=[str(p) for p in result.chunks],
            error=result.error,
        )
        for result in chunk_results
    ]


def build_manifest(
    conversion_results: list[ConversionResult],
    validation_results: dict[Path, ValidationResult],
) -> list[ManifestRecord]:
    """Combine conversion + validation outcomes into manifest records.

    ``validation_results`` should be keyed by the converted output path
    (only present for files that were successfully converted).
    """
    records: list[ManifestRecord] = []
    for result in conversion_results:
        if not result.success or result.output is None:
            records.append(
                ManifestRecord(
                    source_path=str(result.source),
                    output_path=None,
                    status="conversion_failed",
                    error=result.error,
                )
            )
            continue

        validation = validation_results.get(result.output)
        if validation is None or not validation.valid:
            reason = validation.reason if validation else "not validated"
            records.append(
                ManifestRecord(
                    source_path=str(result.source),
                    output_path=str(result.output),
                    status="validation_failed",
                    duration_sec=validation.duration_sec if validation else None,
                    sample_rate=validation.sample_rate if validation else None,
                    channels=validation.channels if validation else None,
                    error=reason,
                )
            )
            continue

        records.append(
            ManifestRecord(
                source_path=str(result.source),
                output_path=str(result.output),
                status="ok",
                duration_sec=validation.duration_sec,
                sample_rate=validation.sample_rate,
                channels=validation.channels,
            )
        )
    return records


def write_manifest(records: list[_RecordT], manifest_path: Path) -> None:
    """Write records to a JSONL file, one record per line."""
    manifest_path = Path(manifest_path)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")
