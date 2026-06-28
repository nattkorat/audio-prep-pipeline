# audio-prep

Convert raw MP3 audio into pretraining-ready WAV/FLAC, with validation and a
dataset manifest as the handoff artifact to the pretraining pipeline.

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
│   ├── manifest.py       # build_manifest, write_manifest (JSONL output)
│   ├── exceptions.py     # ConversionError, ProbeError
│   └── cli.py             # `audio-prep convert ...` entry point
├── tests/
│   ├── conftest.py        # synthetic-audio fixtures (no binary files checked in)
│   ├── test_converter.py
│   ├── test_validator.py
│   ├── test_manifest.py
│   └── test_cli.py
├── .github/workflows/ci.yml   # lint + typecheck + test matrix (3.10-3.12)
├── .pre-commit-config.yaml     # ruff + mypy + basic hygiene hooks, runs on every commit
├── pyproject.toml               # deps, ruff config, mypy config, pytest config
└── Makefile                      # `make check` runs everything CI runs, locally
```

## Pipeline stages

1. **discovery** (`find_audio_files`) — recursively find `.mp3` files under an
   input directory.
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

## Setup

```bash
# ffmpeg is a system dependency, not a pip package
sudo apt-get install ffmpeg   # or: brew install ffmpeg

make install   # pip install -e ".[dev]" + pre-commit install
```

## Usage

```bash
audio-prep convert \
    --input-dir data/raw_mp3 \
    --output-dir data/wav16k \
    --format wav \
    --sample-rate 16000 \
    --workers 8 \
    --manifest data/manifest.jsonl
```

Or import directly for use inside a larger script / notebook:

```python
from audio_prep import ConversionConfig, convert_batch, build_manifest, validate_output

config = ConversionConfig(output_format="wav", sample_rate=16_000, channels=1, num_workers=8)
results = convert_batch("data/raw_mp3", "data/wav16k", config)
validations = {r.output: validate_output(r.output, config) for r in results if r.success}
records = build_manifest(results, validations)
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

- **Resume support**: skip files whose output already exists *and* passes
  validation (currently `overwrite=False` skips on existence alone — fine for
  a first pass, but doesn't catch a previous partial/corrupt write).
- **Source format beyond MP3**: `find_audio_files` already accepts an
  `extensions` tuple — wiring that through the CLI covers `.m4a`/`.ogg`/etc.
  for free since the ffmpeg command doesn't care about input container.
- **Streaming manifest writes** for very large corpora, instead of holding
  all `ConversionResult`s in memory before writing.
- **Silence/VAD-based trimming** as a pre-validation step, if leading/trailing
  silence in source recordings turns out to matter for the pretraining run.

**Note**: This is the template, that you have to extend from. `Main` branch is protected so you have to create another branch to work on.
