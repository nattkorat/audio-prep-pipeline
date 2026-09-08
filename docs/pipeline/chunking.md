# Chunking

Chunking splits source audio into speech-only chunks. It is implemented in
`audio_prep.chunker` and exposed through `audio-prep chunk`.

## Detector

The default detector is Silero VAD. The project tries to load Silero from the
installed `silero-vad` package first, then from `torch.hub`.

Pyannote is also available for comparison by setting `vad_backend="pyannote"` in
Python or `--vad-backend pyannote` in the CLI. The default Pyannote model is
`pyannote/speaker-diarization-community-1`, which is compatible with
`pyannote.audio` 4.x. Some Pyannote models require a Hugging Face token and
accepted model terms, so pass `--hf-token` or set `HF_TOKEN`/`HUGGINGFACE_TOKEN`
when needed.

If the selected detector is unavailable and `allow_energy_fallback=True`,
chunking uses a simple energy-based detector. This fallback is useful for
offline testing but is lower quality than model-based VAD.

## Decode And Resample

Compressed/container sources are decoded through FFmpeg. WAV and FLAC files may
be read directly with `soundfile` when no resampling is needed.

If a sample rate is configured, audio is resampled before VAD and the written
chunks use that rate.

## Duration Rules

- Speech shorter than `min_duration_sec` is dropped.
- Speech longer than `max_duration_sec` is split into windows.
- A source file that produces no chunks returns a failed `ChunkResult`.

## Existing Chunks

When `overwrite=False`, existing chunks are reused only if they are readable and
match the expected sample rate. Corrupt existing chunks are rewritten.

If two source files in the same directory share a stem, such as `clip.mp3` and
`clip.wav`, chunk outputs are written into disambiguated subdirectories such as
`clip_mp3/` and `clip_wav/`.

## CLI Example

<pre><code>audio-prep chunk \
    --input-dir data/raw_mp3 \
    --output-dir data/chunks \
    --format flac \
    --sample-rate 16000 \
    --min-duration-sec 5 \
    --max-duration-sec 20 \
    --workers 4 \
    --manifest data/chunk_manifest.jsonl \
    --profile profiles/chunk-silero.json</code></pre>


Pyannote comparison:

<pre><code>audio-prep chunk \
    --input-dir data/raw_mp3 \
    --output-dir data/chunks-pyannote \
    --sample-rate 16000 \
    --vad-backend pyannote \
    --pyannote-model pyannote/speaker-diarization-community-1 \
    --hf-token "$HF_TOKEN" \
    --profile profiles/chunk-pyannote.json</code></pre>


## Python Example

<pre><code>from pathlib import Path

from audio_prep import ChunkConfig, build_chunk_manifest, chunk_batch, write_manifest

config = ChunkConfig(
    min_duration_sec=5,
    max_duration_sec=20,
    output_format=&quot;flac&quot;,
    sample_rate=16_000,
    num_workers=4,
    vad_backend=&quot;silero&quot;,
)

results = chunk_batch(
    Path(&quot;data/raw_mp3&quot;),
    Path(&quot;data/chunks&quot;),
    config,
)
records = build_chunk_manifest(results)
write_manifest(records, Path(&quot;data/chunk_manifest.jsonl&quot;))</code></pre>


Pyannote comparison from Python:

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

with profiler.measure(&quot;chunk-pyannote&quot;, {&quot;vad_backend&quot;: config.vad_backend}):
    results = chunk_batch(Path(&quot;data/raw_mp3&quot;), Path(&quot;data/chunks-pyannote&quot;), config)

profiler.write_json(
    Path(&quot;profiles/chunk-pyannote.json&quot;),
    operation=&quot;chunk&quot;,
    metadata={&quot;files&quot;: len(results), &quot;vad_backend&quot;: config.vad_backend},
)</code></pre>
