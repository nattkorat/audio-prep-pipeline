# Chunking

Chunking splits source audio into speech-only chunks. It is implemented in
`audio_prep.chunker` and exposed through `audio-prep chunk`.

## Detector

The preferred detector is Silero VAD. The project tries to load Silero from the
installed `silero-vad` package first, then from `torch.hub`.

If Silero is unavailable and `allow_energy_fallback=True`, chunking uses a
simple energy-based detector. This fallback is useful for offline testing but is
lower quality than Silero.

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

## Python Example

<pre><code>from pathlib import Path

from audio_prep import ChunkConfig, chunk_batch

config = ChunkConfig(
    min_duration_sec=5,
    max_duration_sec=20,
    output_format=&quot;flac&quot;,
    sample_rate=16_000,
    num_workers=4,
)

results = chunk_batch(
    Path(&quot;data/raw_mp3&quot;),
    Path(&quot;data/chunks&quot;),
    config,
)</code></pre>
