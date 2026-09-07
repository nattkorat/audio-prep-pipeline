# CLI Reference

The package installs one command:

<pre><code>audio-prep</code></pre>


It has two independent subcommands:

- `convert`: convert source audio files to WAV or FLAC, validate them, and optionally
  write a manifest.
- `chunk`: split source audio files into speech-only chunks and optionally write a
  chunk manifest.

## `audio-prep convert`

<pre><code>audio-prep convert \
    --input-dir data/raw_mp3 \
    --output-dir data/wav16k \
    --format wav \
    --sample-rate 16000 \
    --channels 1 \
    --workers 4 \
    --min-duration-sec 0.5 \
    --manifest data/manifest.jsonl \
    --profile profiles/convert.json</code></pre>


| Flag | Default | Description |
|---|---:|---|
| `--input-dir` | required | Directory scanned recursively for source audio files. |
| `--output-dir` | required | Directory where converted output is written. |
| `--extensions` | common FFmpeg audio/video extensions | Comma-separated source extensions, or `all` to pass every regular file to FFmpeg. |
| `--format` | `wav` | Output format, `wav` or `flac`. |
| `--sample-rate` | `16000` | Target sample rate in Hz. |
| `--channels` | `1` | Target channel count. |
| `--workers` | `4` | Number of parallel conversion workers. |
| `--min-duration-sec` | `0.5` | Minimum accepted output duration. |
| `--overwrite` | off | Rebuild even when an existing output is valid. |
| `--normalize-loudness` | off | Apply single-pass EBU R128 loudness normalization. |
| `--manifest` | none | Path to write conversion manifest JSONL. |
| `--profile` | none | Path to write a JSON profile with wall time, CPU time, and peak RSS. |

Exit codes:

| Code | Meaning |
|---:|---|
| `0` | Every discovered file converted and validated. |
| `1` | At least one file failed conversion or validation. |
| `2` | Argument parsing failed. |

## `audio-prep chunk`

<pre><code>audio-prep chunk \
    --input-dir data/raw_mp3 \
    --output-dir data/chunks \
    --format wav \
    --sample-rate 16000 \
    --min-duration-sec 5 \
    --max-duration-sec 20 \
    --workers 4 \
    --manifest data/chunk_manifest.jsonl \
    --profile profiles/chunk-silero.json</code></pre>


Compare with Pyannote:

<pre><code>audio-prep chunk \
    --input-dir data/raw_mp3 \
    --output-dir data/chunks-pyannote \
    --vad-backend pyannote \
    --pyannote-model pyannote/voice-activity-detection \
    --hf-token "$HF_TOKEN" \
    --profile profiles/chunk-pyannote.json</code></pre>


| Flag | Default | Description |
|---|---:|---|
| `--input-dir` | required | Directory scanned recursively for source audio files. |
| `--output-dir` | `<input-dir>/chunks` | Directory where chunks are written. |
| `--extensions` | common FFmpeg audio/video extensions | Comma-separated source extensions, or `all` to pass every regular file to FFmpeg. |
| `--format` | `wav` | Chunk format, `wav` or `flac`. |
| `--sample-rate` | `16000` | Resample before VAD and chunk writing. |
| `--min-duration-sec` | `5.0` | Drop chunks shorter than this duration. |
| `--max-duration-sec` | `20.0` | Split longer speech into windows no longer than this. |
| `--workers` | `4` | Number of parallel chunking workers. |
| `--overwrite` | off | Rebuild even when an existing chunk is valid. |
| `--vad-backend` | `silero` | Speech detector backend: `silero`, `pyannote`, or `energy`. |
| `--pyannote-model` | `pyannote/voice-activity-detection` | Hugging Face model id used with `--vad-backend pyannote`. |
| `--hf-token` | none | Hugging Face token for gated Pyannote models. Falls back to `HF_TOKEN` or `HUGGINGFACE_TOKEN`. |
| `--allow-energy-fallback` | off | Use a lower-quality energy detector if the selected VAD backend cannot load. |
| `--manifest` | none | Path to write chunk manifest JSONL. |
| `--profile` | none | Path to write a JSON profile with wall time, CPU time, and peak RSS. |

Exit codes:

| Code | Meaning |
|---:|---|
| `0` | Every discovered file produced one or more chunks. |
| `1` | At least one file failed or produced no chunks. |
| `2` | Argument parsing failed. |
