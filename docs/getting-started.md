# Getting Started

This guide gives the shortest path from raw source audio to a validated dataset
manifest.

## Intended Users

Use this project if you prepare speech or general audio corpora for pretraining,
ASR experiments, or downstream dataset curation. It is especially useful when a
large corpus may contain bad files and you need a manifest showing exactly what
worked and what failed.

## Expected Input

The CLI scans for common FFmpeg-readable audio/video containers under an input directory:

<pre><code>data/raw_mp3/
├── speaker_a/
│   ├── clip_001.mp3
│   └── clip_002.mp3
└── speaker_b/
    └── clip_001.mp3</code></pre>


Discovery is recursive and deterministic. It ignores files with unsupported extensions by
default. Use `--extensions all` to pass every regular file to FFmpeg and record
unsupported inputs as per-file failures.

## Expected Output

The conversion command mirrors the input directory structure under the output
directory:

<pre><code>data/wav16k/
├── speaker_a/
│   ├── clip_001.wav
│   └── clip_002.wav
└── speaker_b/
    └── clip_001.wav</code></pre>


If a manifest path is provided, each source file gets one JSONL record with a
status:

| Status | Meaning |
|---|---|
| `ok` | Conversion succeeded and validation passed. |
| `conversion_failed` | FFmpeg could not decode or write the file. |
| `validation_failed` | Output exists but does not match the requested spec. |

## Basic Workflow

1. Install Python dependencies and FFmpeg.
2. Run `audio-prep convert` against the raw source audio directory.
3. Inspect the manifest for failed files.
4. Optionally run `audio-prep chunk` to create speech-only segments.

Example command:

<pre><code>audio-prep convert \
    --input-dir data/raw_mp3 \
    --output-dir data/wav16k \
    --manifest data/manifest.jsonl</code></pre>


The default conversion target is 16 kHz mono WAV. Override it only when the
downstream model expects a different audio spec.

## Resume Behavior

With `--overwrite` off, conversion skips an existing output only when it passes
the same validation checks as a newly converted file. Empty, corrupt, too-short,
or wrong-spec outputs are replaced automatically.

Use `--overwrite` when you want to force regeneration even for valid existing
outputs.
