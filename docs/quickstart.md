# Quick Start

## Convert Source Audio To 16 kHz Mono WAV

<pre><code>audio-prep convert \
    --input-dir data/raw_mp3 \
    --output-dir data/wav16k \
    --workers 4 \
    --manifest data/manifest.jsonl</code></pre>


Expected result:

- Converted files under `data/wav16k`
- Matching subdirectories from `data/raw_mp3`
- A JSONL manifest at `data/manifest.jsonl`
- Exit code `0` if every file converted and validated
- Exit code `1` if any file failed conversion or validation

## Convert To FLAC

<pre><code>audio-prep convert \
    --input-dir data/raw_mp3 \
    --output-dir data/flac16k \
    --format flac \
    --manifest data/flac_manifest.jsonl</code></pre>


## Force Rebuild Existing Outputs

<pre><code>audio-prep convert \
    --input-dir data/raw_mp3 \
    --output-dir data/wav16k \
    --overwrite</code></pre>


Without `--overwrite`, valid existing outputs are reused and invalid existing
outputs are replaced.

## Chunk Speech

Install chunking dependencies first:

<pre><code>pip install -e &quot;.[chunking]&quot;</code></pre>


Then run:

<pre><code>audio-prep chunk \
    --input-dir data/raw_mp3 \
    --output-dir data/chunks \
    --min-duration-sec 5 \
    --max-duration-sec 20 \
    --workers 4 \
    --manifest data/chunk_manifest.jsonl</code></pre>


Use `--allow-energy-fallback` only when Silero VAD is not available and an
approximate offline detector is acceptable.
