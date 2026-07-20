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

CLI conversion:

<pre><code>audio-prep convert \
    --input-dir data/raw_mp3 \
    --output-dir data/wav16k \
    --format wav \
    --sample-rate 16000 \
    --workers 8 \
    --manifest data/manifest.jsonl</code></pre>


Python conversion:

<pre><code>from pathlib import Path

from audio_prep import ConversionConfig, build_manifest, convert_batch, validate_output, write_manifest

config = ConversionConfig(output_format=&quot;wav&quot;, sample_rate=16_000, num_workers=8)
results = convert_batch(Path(&quot;data/raw_mp3&quot;), Path(&quot;data/wav16k&quot;), config)
validations = {
    result.output: validate_output(result.output, config)
    for result in results
    if result.success and result.output is not None
}
records = build_manifest(results, validations)
write_manifest(records, Path(&quot;data/manifest.jsonl&quot;))</code></pre>


CLI chunking:

<pre><code>audio-prep chunk \
    --input-dir data/raw_mp3 \
    --output-dir data/chunks \
    --min-duration-sec 5 \
    --max-duration-sec 20 \
    --manifest data/chunk_manifest.jsonl</code></pre>


Python chunking:

<pre><code>from pathlib import Path

from audio_prep import ChunkConfig, build_chunk_manifest, chunk_batch, write_manifest

config = ChunkConfig(min_duration_sec=5, max_duration_sec=20)
results = chunk_batch(Path(&quot;data/raw_mp3&quot;), Path(&quot;data/chunks&quot;), config)
records = build_chunk_manifest(results)
write_manifest(records, Path(&quot;data/chunk_manifest.jsonl&quot;))</code></pre>


## Start Here

- [Getting Started](getting-started.md)
- [Installation](installation.md)
- [CLI Reference](cli.md)
- [Pipeline Overview](pipeline/overview.md)

## Project Links

- [PyPI package](https://pypi.org/project/audio-prep-pipeline/)
- [GitHub repository](https://github.com/nattkorat/audio-prep-pipeline)
