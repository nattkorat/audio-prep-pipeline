"""Command-line entry point.

    audio-prep convert --input-dir data/raw_mp3 --output-dir data/wav16k \\
        --format wav --sample-rate 16000 --workers 8 --manifest data/manifest.jsonl
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

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


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "convert":
        return run_convert(args)

    parser.error(f"unknown command: {args.command}")
    return 2  # unreachable, parser.error exits


if __name__ == "__main__":
    sys.exit(main())
