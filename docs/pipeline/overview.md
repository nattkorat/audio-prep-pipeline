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
