# Pipeline Overview

`audio-prep` has two independent pipelines.

## Conversion Pipeline

<pre><code>Raw source audio
  -&gt; discovery
  -&gt; FFmpeg conversion
  -&gt; validation
  -&gt; JSONL manifest
  -&gt; training-ready WAV or FLAC files</code></pre>


Conversion failures do not abort the whole run. Each source file receives a
result, and failed files can be inspected through the manifest.

## Chunking Pipeline

<pre><code>Raw source audio
  -&gt; discovery
  -&gt; FFmpeg decode and optional resample
  -&gt; VAD speech detection
  -&gt; chunk writing
  -&gt; JSONL chunk manifest</code></pre>


Chunking is separate from conversion. The `chunk` command scans source audio files
directly and writes chunks without first running `convert`.

## Deterministic Output

Discovery returns sorted file paths so sequential and parallel runs produce
results in the same order. Output paths mirror source subdirectories under the
chosen output directory.

## CLI Or Python

Run the pipelines directly from the command line:

<pre><code>audio-prep convert \
    --input-dir data/raw_mp3 \
    --output-dir data/wav16k \
    --manifest data/manifest.jsonl

audio-prep chunk \
    --input-dir data/raw_mp3 \
    --output-dir data/chunks \
    --manifest data/chunk_manifest.jsonl</code></pre>


Or call the same pipeline functions from Python:

<pre><code>from pathlib import Path

from audio_prep import ChunkConfig, ConversionConfig, chunk_batch, convert_batch

converted = convert_batch(
    Path(&quot;data/raw_mp3&quot;),
    Path(&quot;data/wav16k&quot;),
    ConversionConfig(),
)

chunks = chunk_batch(
    Path(&quot;data/raw_mp3&quot;),
    Path(&quot;data/chunks&quot;),
    ChunkConfig(),
)</code></pre>
