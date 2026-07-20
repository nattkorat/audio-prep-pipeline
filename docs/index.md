# Audio Prep Pipeline

`audio-prep` converts source audio into pretraining-ready WAV or FLAC files and
can optionally split speech into VAD-based chunks. It is designed for dataset
preparation before self-supervised speech pretraining workflows such as
Wav2Vec2 and XLS-R.

Default converted output:

| Setting | Default |
|---|---:|
| Format | WAV |
| Sample rate | 16 kHz |
| Channels | 1, mono |

## What It Does

The conversion pipeline:

1. Recursively discovers supported source audio files.
2. Converts audio with FFmpeg.
3. Validates output with `soundfile`.
4. Writes an optional JSONL manifest.

The chunking pipeline:

1. Recursively discovers supported source audio files.
2. Decodes audio with FFmpeg.
3. Detects speech with Silero VAD, or an optional energy fallback.
4. Writes speech-only WAV or FLAC chunks.
5. Writes an optional JSONL chunk manifest.

## Why This Exists

Large audio corpora often contain corrupt files, inconsistent sample rates,
wrong channel layouts, very short clips, and silence-heavy recordings. This
project keeps those problems visible by returning per-file results instead of
aborting entire batch jobs, and by validating generated files before they are
handed to training code.

## Quick Example

<pre><code>audio-prep convert \
    --input-dir data/raw_mp3 \
    --output-dir data/wav16k \
    --format wav \
    --sample-rate 16000 \
    --workers 8 \
    --manifest data/manifest.jsonl</code></pre>


For speech chunking:

<pre><code>audio-prep chunk \
    --input-dir data/raw_mp3 \
    --output-dir data/chunks \
    --min-duration-sec 5 \
    --max-duration-sec 20 \
    --manifest data/chunk_manifest.jsonl</code></pre>


## Start Here

- [Getting Started](getting-started.md)
- [Installation](installation.md)
- [CLI Reference](cli.md)
- [Pipeline Overview](pipeline/overview.md)
