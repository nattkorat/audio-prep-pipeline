# Quick Start

## Convert Source Audio To 16 kHz Mono WAV

CLI:

<pre><code>audio-prep convert \
    --input-dir data/raw_mp3 \
    --output-dir data/wav16k \
    --workers 4 \
    --manifest data/manifest.jsonl</code></pre>


Python:

<pre><code>from pathlib import Path

from audio_prep import ConversionConfig, build_manifest, convert_batch, validate_output, write_manifest

config = ConversionConfig(num_workers=4)
results = convert_batch(Path(&quot;data/raw_mp3&quot;), Path(&quot;data/wav16k&quot;), config)
validations = {
    result.output: validate_output(result.output, config)
    for result in results
    if result.success and result.output is not None
}
records = build_manifest(results, validations)
write_manifest(records, Path(&quot;data/manifest.jsonl&quot;))</code></pre>


Expected result:

- Converted files under `data/wav16k`
- Matching subdirectories from `data/raw_mp3`
- A JSONL manifest at `data/manifest.jsonl`
- Exit code `0` if every file converted and validated
- Exit code `1` if any file failed conversion or validation

## Convert To FLAC

CLI:

<pre><code>audio-prep convert \
    --input-dir data/raw_mp3 \
    --output-dir data/flac16k \
    --format flac \
    --manifest data/flac_manifest.jsonl</code></pre>


Python:

<pre><code>from pathlib import Path

from audio_prep import ConversionConfig, build_manifest, convert_batch, validate_output, write_manifest

config = ConversionConfig(output_format=&quot;flac&quot;, num_workers=4)
results = convert_batch(Path(&quot;data/raw_mp3&quot;), Path(&quot;data/flac16k&quot;), config)
validations = {
    result.output: validate_output(result.output, config)
    for result in results
    if result.success and result.output is not None
}
records = build_manifest(results, validations)
write_manifest(records, Path(&quot;data/flac_manifest.jsonl&quot;))</code></pre>


## Force Rebuild Existing Outputs

CLI:

<pre><code>audio-prep convert \
    --input-dir data/raw_mp3 \
    --output-dir data/wav16k \
    --overwrite</code></pre>


Python:

<pre><code>from pathlib import Path

from audio_prep import ConversionConfig, convert_batch

config = ConversionConfig(overwrite=True)
results = convert_batch(Path(&quot;data/raw_mp3&quot;), Path(&quot;data/wav16k&quot;), config)</code></pre>


Without `--overwrite`, valid existing outputs are reused and invalid existing
outputs are replaced.

## Chunk Speech

CLI:

<pre><code>audio-prep chunk \
    --input-dir data/raw_mp3 \
    --output-dir data/chunks \
    --min-duration-sec 5 \
    --max-duration-sec 20 \
    --workers 4 \
    --manifest data/chunk_manifest.jsonl</code></pre>


Python:

<pre><code>from pathlib import Path

from audio_prep import ChunkConfig, build_chunk_manifest, chunk_batch, write_manifest

config = ChunkConfig(min_duration_sec=5, max_duration_sec=20, num_workers=4)
results = chunk_batch(Path(&quot;data/raw_mp3&quot;), Path(&quot;data/chunks&quot;), config)
records = build_chunk_manifest(results)
write_manifest(records, Path(&quot;data/chunk_manifest.jsonl&quot;))</code></pre>


Use `--allow-energy-fallback` only when Silero VAD is not available and an
approximate offline detector is acceptable.
