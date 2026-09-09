# Profiling

Profiling records wall time, CPU time, child-process CPU time, and peak resident
memory. The CLI writes JSON reports with one record per pipeline stage.

## CLI Example

Conversion:

<pre><code>audio-prep convert \
    --input-dir data/raw_mp3 \
    --output-dir data/wav16k \
    --profile profiles/convert.json</code></pre>


Chunking with Silero:

<pre><code>audio-prep chunk \
    --input-dir data/raw_mp3 \
    --output-dir data/chunks-silero \
    --vad-backend silero \
    --profile profiles/chunk-silero.json</code></pre>


Chunking with Pyannote:

<pre><code>audio-prep chunk \
    --input-dir data/raw_mp3 \
    --output-dir data/chunks-pyannote \
    --vad-backend pyannote \
    --pyannote-model pyannote/speaker-diarization-community-1 \
    --hf-token "$HF_TOKEN" \
    --profile profiles/chunk-pyannote.json</code></pre>


Use the same input directory, sample rate, chunk duration settings, and worker
count when comparing detector backends. For the clearest single-model timing,
set `--workers 1`.

## Python Example

<pre><code>from pathlib import Path

from audio_prep import ChunkConfig, Profiler, chunk_batch

profiler = Profiler()
config = ChunkConfig(
    min_duration_sec=5,
    max_duration_sec=20,
    sample_rate=16_000,
    num_workers=1,
    vad_backend=&quot;pyannote&quot;,
    pyannote_model=&quot;pyannote/speaker-diarization-community-1&quot;,
)

with profiler.measure(&quot;chunk&quot;, {&quot;vad_backend&quot;: config.vad_backend}):
    results = chunk_batch(Path(&quot;data/raw_mp3&quot;), Path(&quot;data/chunks-pyannote&quot;), config)

profiler.write_json(
    Path(&quot;profiles/chunk-pyannote.json&quot;),
    operation=&quot;chunk&quot;,
    metadata={&quot;files&quot;: len(results), &quot;vad_backend&quot;: config.vad_backend},
)</code></pre>


## Report Shape

The JSON report contains:

| Field | Meaning |
|---|---|
| `operation` | `convert` or `chunk`. |
| `metadata` | Run-level inputs such as backend, worker count, and file counts. |
| `summary.elapsed_sec` | Sum of measured stage wall times. |
| `summary.total_cpu_sec` | Sum of self and child CPU time across measured stages. |
| `summary.self_max_rss_mb` | Peak resident memory for the current process. |
| `summary.children_max_rss_mb` | Peak resident memory reported for child processes. |
| `records` | Per-stage measurements such as `discover`, `convert`, `chunk`, `validate`, and `manifest`. |
