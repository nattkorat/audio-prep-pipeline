"""MP3 -> WAV/FLAC conversion, backed by ffmpeg.

Why shell out to ffmpeg rather than a pure-Python decoder: MP3 decoding
quality/robustness across the long tail of real-world files (VBR, odd
headers, ID3 variants) is handled far more reliably by ffmpeg than by
any pure-Python library, and it's the same tool most ASR pretraining
pipelines (fairseq, ESPnet, HF examples) lean on under the hood.
"""

from __future__ import annotations

import logging
import subprocess
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

from audio_prep.config import ConversionConfig
from audio_prep.exceptions import ConversionError

logger = logging.getLogger(__name__)

DEFAULT_SOURCE_EXTENSIONS = (".mp3",)


@dataclass(slots=True)
class ConversionResult:
    """Outcome of converting a single source file."""

    source: Path
    output: Path | None
    success: bool
    error: str | None = None


def find_audio_files(
    input_dir: Path,
    extensions: tuple[str, ...] = DEFAULT_SOURCE_EXTENSIONS,
) -> list[Path]:
    """Recursively find source audio files under ``input_dir``.

    Matching is case-insensitive on the extension. Files are returned in
    sorted order so pipeline runs are deterministic.
    """
    input_dir = Path(input_dir)
    if not input_dir.is_dir():
        raise FileNotFoundError(f"input_dir does not exist or is not a directory: {input_dir}")

    lowered = {ext.lower() for ext in extensions}
    matches = [p for p in input_dir.rglob("*") if p.is_file() and p.suffix.lower() in lowered]
    return sorted(matches)


def _build_ffmpeg_cmd(source: Path, dest: Path, config: ConversionConfig) -> list[str]:
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y" if config.overwrite else "-n",
        "-i",
        str(source),
        "-ar",
        str(config.sample_rate),
        "-ac",
        str(config.channels),
    ]
    if config.normalize_loudness:
        # EBU R128 single-pass loudness normalization to -23 LUFS.
        cmd += ["-af", "loudnorm=I=-23:LRA=7:TP=-2"]
    if config.output_format == "flac":
        cmd += ["-f", "flac"]
    else:
        cmd += ["-f", "wav", "-c:a", "pcm_s16le"]
    cmd.append(str(dest))
    return cmd


def convert_file(source: Path, dest: Path, config: ConversionConfig) -> ConversionResult:
    """Convert a single source file to the target format/spec.

    Returns a :class:`ConversionResult` rather than raising on failure so
    batch runs can collect partial results instead of aborting on the
    first bad file in a large corpus.
    """
    source = Path(source)
    dest = Path(dest)

    if not source.is_file():
        return ConversionResult(source, None, success=False, error=f"source not found: {source}")

    if dest.exists() and not config.overwrite:
        return ConversionResult(source, dest, success=True, error=None)

    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = _build_ffmpeg_cmd(source, dest, config)

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except FileNotFoundError as exc:
        # ffmpeg binary itself missing from PATH
        return ConversionResult(source, None, success=False, error=str(exc))

    if proc.returncode != 0:
        err = ConversionError(str(source), proc.returncode, proc.stderr)
        logger.warning(str(err))
        return ConversionResult(source, None, success=False, error=str(err))

    return ConversionResult(source, dest, success=True, error=None)


def _dest_for(source: Path, input_dir: Path, output_dir: Path, config: ConversionConfig) -> Path:
    relative = source.relative_to(input_dir).with_suffix(f".{config.output_format}")
    return output_dir / relative


def convert_batch(
    input_dir: Path,
    output_dir: Path,
    config: ConversionConfig | None = None,
    source_files: list[Path] | None = None,
) -> list[ConversionResult]:
    """Convert every source file under ``input_dir`` into ``output_dir``.

    Mirrors the input directory's relative subfolder structure. Uses a
    process pool since ffmpeg conversion is CPU-bound subprocess work.

    Pass ``source_files`` to convert a pre-filtered list instead of
    re-discovering files (useful for tests and for resuming partial runs).
    """
    config = config or ConversionConfig()
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)

    files = source_files if source_files is not None else find_audio_files(input_dir)
    if not files:
        logger.warning("No source audio files found under %s", input_dir)
        return []

    jobs = [(f, _dest_for(f, input_dir, output_dir, config)) for f in files]

    if config.num_workers == 1:
        return [convert_file(src, dst, config) for src, dst in jobs]

    results: list[ConversionResult] = []
    with ProcessPoolExecutor(max_workers=config.num_workers) as pool:
        futures = {pool.submit(convert_file, src, dst, config): src for src, dst in jobs}
        for future in as_completed(futures):
            results.append(future.result())

    # Keep output order deterministic regardless of completion order.
    order = {src: i for i, (src, _dst) in enumerate(jobs)}
    results.sort(key=lambda r: order[r.source])
    return results
