"""Command-line entry point.

    audio-prep convert --input-dir data/raw_mp3 --output-dir data/wav16k \\
        --format wav --sample-rate 16000 --workers 8 --manifest data/manifest.jsonl

    audio-prep chunk --input-dir data/raw_mp3 --output-dir data/chunks \\
        --sample-rate 16000 --format flac --min-duration-sec 5 --max-duration-sec 20
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from audio_prep.chunker import SUPPORTED_CHUNK_FORMATS
from audio_prep.config import SUPPORTED_OUTPUT_FORMATS, ConversionConfig
from audio_prep.converter import convert_batch, find_audio_files
from audio_prep.manifest import build_manifest, write_manifest
from audio_prep.validator import validate_output

logger = logging.getLogger("audio_prep")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="audio-prep")
    sub = parser.add_subparsers(dest="command", required=True)

    convert = sub.add_parser("convert", help="convert MP3s into pretraining-ready WAV/FLAC")
    convert.add_argument("--input-dir", type=Path, required=True)
    convert.add_argument("--output-dir", type=Path, required=True)
    convert.add_argument("--format", choices=SUPPORTED_OUTPUT_FORMATS, default="wav")
    convert.add_argument("--sample-rate", type=int, default=16_000)
    convert.add_argument("--channels", type=int, default=1)
    convert.add_argument("--workers", type=int, default=4)
    convert.add_argument("--min-duration-sec", type=float, default=0.5)
    convert.add_argument("--overwrite", action="store_true")
    convert.add_argument("--normalize-loudness", action="store_true")
    convert.add_argument(
        "--manifest", type=Path, default=None, help="path to write a JSONL manifest"
    )

    chunk = sub.add_parser(
        "chunk", help="run VAD speech chunking directly against a directory of MP3s"
    )
    chunk.add_argument("--input-dir", type=Path, required=True, help="directory of source MP3s")
    chunk.add_argument(
        "--output-dir", type=Path, default=None, help="defaults to <input-dir>/chunks"
    )
    chunk.add_argument("--format", choices=SUPPORTED_CHUNK_FORMATS, default="wav")
    chunk.add_argument(
        "--sample-rate",
        type=int,
        default=16_000,
        help="resample (via ffmpeg) to this rate before chunking if the source doesn't "
        "already match it",
    )
    chunk.add_argument("--min-duration-sec", type=float, default=5.0)
    chunk.add_argument("--max-duration-sec", type=float, default=20.0)
    chunk.add_argument("--workers", type=int, default=4)
    chunk.add_argument("--overwrite", action="store_true")
    chunk.add_argument(
        "--allow-energy-fallback",
        action="store_true",
        help="fall back to a low-quality energy-based detector if Silero VAD can't be loaded",
    )
    chunk.add_argument(
        "--manifest", type=Path, default=None, help="path to write a JSONL chunk manifest"
    )

    return parser


def run_convert(args: argparse.Namespace) -> int:
    config = ConversionConfig(
        output_format=args.format,
        sample_rate=args.sample_rate,
        channels=args.channels,
        num_workers=args.workers,
        min_duration_sec=args.min_duration_sec,
        overwrite=args.overwrite,
        normalize_loudness=args.normalize_loudness,
    )

    files = find_audio_files(args.input_dir)
    logger.info("Found %d source file(s) under %s", len(files), args.input_dir)

    results = convert_batch(args.input_dir, args.output_dir, config, source_files=files)
    n_ok = sum(1 for r in results if r.success)
    logger.info("Conversion: %d/%d succeeded", n_ok, len(results))

    validations = {
        r.output: validate_output(r.output, config) for r in results if r.success and r.output
    }
    n_valid = sum(1 for v in validations.values() if v.valid)
    logger.info("Validation: %d/%d passed", n_valid, len(validations))

    if args.manifest:
        records = build_manifest(results, validations)
        write_manifest(records, args.manifest)
        logger.info("Manifest written to %s (%d records)", args.manifest, len(records))

    n_failed = len(results) - n_valid
    return 1 if n_failed else 0


def run_chunk(args: argparse.Namespace) -> int:
    # Imported lazily: chunking needs the 'chunking' extra (torch +
    # silero-vad) to actually run, even though importing the module itself
    # doesn't.
    from audio_prep.chunker import ChunkConfig, chunk_batch

    output_dir = args.output_dir or (args.input_dir / "chunks")
    config = ChunkConfig(
        min_duration_sec=args.min_duration_sec,
        max_duration_sec=args.max_duration_sec,
        output_format=args.format,
        sample_rate=args.sample_rate,
        num_workers=args.workers,
        overwrite=args.overwrite,
        allow_energy_fallback=args.allow_energy_fallback,
    )

    results = chunk_batch(args.input_dir, output_dir, config)
    n_ok = sum(1 for r in results if r.success)
    n_chunks = sum(len(r.chunks) for r in results)
    logger.info(
        "Chunking: %d/%d file(s) produced %d speech chunk(s) in %s",
        n_ok,
        len(results),
        n_chunks,
        output_dir,
    )

    if args.manifest:
        from audio_prep.manifest import build_chunk_manifest, write_manifest

        records = build_chunk_manifest(results)
        write_manifest(records, args.manifest)
        logger.info("Manifest written to %s (%d records)", args.manifest, len(records))

    return 1 if n_ok < len(results) else 0


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "convert":
        return run_convert(args)
    if args.command == "chunk":
        return run_chunk(args)

    parser.error(f"unknown command: {args.command}")
    return 2  # unreachable, parser.error exits


if __name__ == "__main__":
    sys.exit(main())
