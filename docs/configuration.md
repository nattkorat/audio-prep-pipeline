# Configuration

Configuration is represented by immutable dataclasses in Python and by CLI
flags for command-line use.

## Conversion Defaults

`ConversionConfig` controls conversion and validation:

| Field | Default | Meaning |
|---|---:|---|
| `output_format` | `wav` | Converted format, `wav` or `flac`. |
| `sample_rate` | `16000` | Target sample rate. |
| `channels` | `1` | Target channel count. |
| `num_workers` | `4` | Parallel conversion workers. |
| `min_duration_sec` | `0.5` | Minimum valid output duration. |
| `overwrite` | `False` | Force regeneration of existing outputs. |
| `normalize_loudness` | `False` | Apply FFmpeg `loudnorm`. |

Example:

<pre><code>from audio_prep import ConversionConfig

config = ConversionConfig(
    output_format=&quot;flac&quot;,
    sample_rate=16_000,
    channels=1,
    num_workers=8,
)</code></pre>


Invalid values raise `ValueError`.

## Chunking Defaults

`ChunkConfig` controls VAD chunking:

| Field | Default | Meaning |
|---|---:|---|
| `min_duration_sec` | `5.0` | Drop chunks shorter than this duration. |
| `max_duration_sec` | `20.0` | Split longer speech into windows at this duration. |
| `output_format` | `wav` | Chunk format, `wav` or `flac`. |
| `sample_rate` | `None` | Preserve native rate unless a target is supplied. |
| `num_workers` | `1` | Parallel chunking workers for Python API use. |
| `overwrite` | `False` | Force regeneration of valid existing chunks. |
| `allow_energy_fallback` | `False` | Use the energy detector if Silero cannot load. |

Example:

<pre><code>from audio_prep import ChunkConfig

config = ChunkConfig(
    min_duration_sec=5,
    max_duration_sec=20,
    output_format=&quot;flac&quot;,
    sample_rate=16_000,
    num_workers=4,
)</code></pre>


The CLI sets `--sample-rate 16000` for chunking by default. The Python API
default is `None`, which preserves the source sample rate.
