# audio-prep

[![CI](https://github.com/nattkorat/audio-prep-pipeline/actions/workflows/ci.yml/badge.svg)](https://github.com/nattkorat/audio-prep-pipeline/actions/workflows/ci.yml)
![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)
![Code style: Ruff](https://img.shields.io/badge/code%20style-ruff-46a2f1)
![Type checked: mypy](https://img.shields.io/badge/type%20checked-mypy-blue)
![Requires FFmpeg](https://img.shields.io/badge/requires-FFmpeg-007808)


Convert source audio into pretraining-ready WAV/FLAC, with validation and a
dataset manifest as the handoff artifact to the pretraining pipeline. Discovery
supports common FFmpeg-readable audio/video containers by default and can scan
all files with `--extensions all`.

Defaults: **16 kHz, mono** — the standard input spec for Wav2Vec2 / XLS-R
style self-supervised speech pretraining. Override via CLI flags if a
different downstream model needs something else.

## Repo layout

```
audio-prep-pipeline/
├── src/audio_prep/
│   ├── config.py        # ConversionConfig: target spec + behavior knobs
│   ├── converter.py      # find_audio_files, convert_file, convert_batch
│   ├── validator.py      # probe_duration, validate_output
│   ├── chunker.py         # (optional) ChunkConfig, chunk_file, chunk_batch -- Silero VAD speech chunking
│   ├── manifest.py       # build_manifest, write_manifest (JSONL output)
│   ├── exceptions.py     # ConversionError, ProbeError, ChunkingError
│   └── cli.py             # `audio-prep convert ...` / `audio-prep chunk ...` entry point
├── tests/
│   ├── conftest.py        # synthetic-audio fixtures (no binary files checked in)
│   ├── test_converter.py
│   ├── test_validator.py
│   ├── test_chunker.py    # fake-detector tests, no real VAD model needed
│   ├── test_manifest.py
│   └── test_cli.py
├── .github/workflows/ci.yml   # lint + typecheck + test matrix (3.10-3.12)
├── .pre-commit-config.yaml     # ruff + mypy + basic hygiene hooks, runs on every commit
├── pyproject.toml               # deps, ruff config, mypy config, pytest config
└── Makefile                      # `make check` runs everything CI runs, locally
```

## Commands

`audio-prep` has two independent subcommands. Neither depends on the other
running first -- both scan `--input-dir` for supported source files directly.

- **`audio-prep convert`** - conversion only: `ffmpeg` resample/remix/re-encode
  into the target WAV/FLAC spec, then validation, then an optional manifest.
  Does not chunk.
- **`audio-prep chunk`** - chunking only: Silero VAD speech chunking straight
  from source audio, with its own resample/format/manifest options. Does not convert
  or validate.

### `convert` pipeline stages

1. **discovery** (`find_audio_files`) — recursively find supported source files
   under an input directory.
2. **conversion** (`convert_file` / `convert_batch`) — shell out to `ffmpeg` to
   resample/remix/re-encode into the target WAV/FLAC spec. Mirrors the input
   directory's subfolder structure on output. Runs in a process pool since
   each conversion is an independent subprocess call.
3. **validation** (`validate_output`) — re-opens each converted file with
   `soundfile` and checks it actually matches the requested sample rate,
   channel count, and minimum duration. This catches the case where ffmpeg
   exits 0 but silently produced something degenerate.
4. **manifest** (`build_manifest` / `write_manifest`) — JSONL file, one row
   per source file, recording `status` (`ok` / `conversion_failed` /
   `validation_failed`), output path, duration, sample rate, and any error.

Conversion failures don't abort the batch — a bad file in a 50,000-file
corpus shows up as one `conversion_failed` row in the manifest, not a crashed
job three hours in.

### `chunk` pipeline stages

1. **discovery** (`find_audio_files`) — recursively find supported source files
   under an input directory.
2. **chunking** (`chunk_file` / `chunk_batch`) — runs Silero VAD over each
   file (decoding/resampling via ffmpeg) and splits it into speech-only
   chunks bounded by a `[min, max]` duration window, so silence-heavy source
   recordings don't waste pretraining compute. Needs the `chunking` extra
   (`torch` + `silero-vad`, see Setup below).
3. **manifest** (`build_chunk_manifest` / `write_manifest`), optional — JSONL
   file, one row per source file, recording `status` (`ok` /
   `chunking_failed`), chunk count, and chunk paths.

Chunking failures (e.g. no speech detected) work the same way: `chunk_batch`
returns a `ChunkResult` per file instead of raising.

## Setup

```bash
# ffmpeg is a system dependency, not a pip package
sudo apt-get install ffmpeg   # or: brew install ffmpeg

make install   # pip install -e ".[dev]" + pre-commit install
```

Chunking needs an extra install -- `make install` alone does not pull in
`torch`/`silero-vad`/`tqdm`, since `convert` doesn't need them:

```bash
pip install -e ".[chunking]"
```

The first `chunk` run needs either the `silero-vad` pip package installed, or
network access so `torch.hub` can download `snakers4/silero-vad` once (it's
then cached under `~/.cache/torch/hub`). If neither is available, pass
`--allow-energy-fallback` to use a lower-quality offline detector instead of
failing.

## Usage

### `audio-prep convert`

```bash
audio-prep convert \
    --input-dir data/raw_mp3 \
    --output-dir data/wav16k \
    --format wav \
    --sample-rate 16000 \
    --workers 8 \
    --manifest data/manifest.jsonl
```

| Flag | Default | Meaning |
|---|---|---|
| `--input-dir` | *(required)* | directory of source audio files |
| `--output-dir` | *(required)* | where converted output is written |
| `--extensions` | common FFmpeg audio/video extensions | comma-separated source extensions, or `all` to pass every regular file to FFmpeg |
| `--format` | `wav` | output format (`wav` or `flac`) |
| `--sample-rate` | 16000 | target sample rate |
| `--channels` | 1 | target channel count |
| `--workers` | 4 | parallel conversion workers |
| `--min-duration-sec` | 0.5 | validation fails files shorter than this |
| `--overwrite` | off | re-convert even if output already exists and passes validation |
| `--normalize-loudness` | off | apply EBU R128 loudness normalization (-23 LUFS) |
| `--manifest` | none | path to write a JSONL manifest |

### `audio-prep chunk`

Independent of `convert` -- scans `--input-dir` for supported source files and runs VAD
chunking directly against them, decoding (and resampling, if `--sample-rate`
doesn't match the source) via ffmpeg:

```bash
audio-prep chunk \
    --input-dir data/raw_mp3 \
    --output-dir data/chunks \
    --sample-rate 16000 \
    --format flac \
    --min-duration-sec 5 \
    --max-duration-sec 20 \
    --workers 4 \
    --manifest data/chunk_manifest.jsonl
```

| Flag | Default | Meaning |
|---|---|---|
| `--input-dir` | *(required)* | directory of source audio files to scan and chunk |
| `--output-dir` | `<input-dir>/chunks` | where chunks are written |
| `--extensions` | common FFmpeg audio/video extensions | comma-separated source extensions, or `all` to pass every regular file to FFmpeg |
| `--format` | `wav` | output chunk format (`wav` or `flac`) |
| `--sample-rate` | 16000 | resample (via ffmpeg) to this rate before chunking if the source doesn't already match it |
| `--min-duration-sec` | 5.0 | drop chunks shorter than this |
| `--max-duration-sec` | 20.0 | split longer speech into windows this size |
| `--workers` | 4 | parallel chunking workers |
| `--overwrite` | off | re-chunk even if valid output already exists |
| `--allow-energy-fallback` | off | fall back to a low-quality energy detector if Silero can't load, instead of raising |
| `--manifest` | none | path to write a JSONL chunk manifest (source file, status, chunk count/paths) |

`chunk_file` itself doesn't care about source extension -- it decodes
whatever path it's given -- so the Python API can also chunk an existing
WAV/FLAC corpus (e.g. `convert_batch` output) by passing `source_files`
explicitly instead of relying on `chunk_batch` discovery:

```python
from audio_prep import ConversionConfig, convert_batch, build_manifest, validate_output
from audio_prep import ChunkConfig, chunk_batch

config = ConversionConfig(output_format="wav", sample_rate=16_000, channels=1, num_workers=8)
results = convert_batch("data/raw_mp3", "data/wav16k", config)
validations = {r.output: validate_output(r.output, config) for r in results if r.success}
records = build_manifest(results, validations)

# source_files bypasses chunk_batch discovery, so this works
# directly against the already-converted WAV output above.
valid_outputs = [path for path, v in validations.items() if v.valid]
chunk_config = ChunkConfig(min_duration_sec=5, max_duration_sec=20, num_workers=4)
chunk_results = chunk_batch("data/wav16k", "data/wav16k/chunks", chunk_config, source_files=valid_outputs)
```

## Development workflow

```bash
make format     # ruff format + autofix
make lint       # ruff check
make typecheck  # mypy --strict
make test       # pytest with coverage
make check      # all of the above -- run this before opening a PR
```

`pre-commit` (installed via `make install`) runs ruff + mypy + basic hygiene
checks automatically on every commit. CI (`.github/workflows/ci.yml`) re-runs
the same checks plus the full test matrix across Python 3.10–3.12 on every
push and PR.

## Extending this

Natural next additions, in roughly the order they'd come up:

- **Streaming manifest writes** for very large corpora, instead of holding
  all `ConversionResult`s in memory before writing.

**Note**: This is the template, that you have to extend from. `Main` branch is protected so you have to create another branch to work on.
