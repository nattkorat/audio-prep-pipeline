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

CLI:

<pre><code>audio-prep convert \
    --input-dir data/raw_mp3 \
    --output-dir data/flac16k \
    --format flac \
    --sample-rate 16000 \
    --channels 1 \
    --workers 8</code></pre>


Python:

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
| `allow_energy_fallback` | `False` | Use the energy detector if the selected VAD cannot load. |
| `vad_backend` | `silero` | Speech detector backend: `silero`, `pyannote`, or `energy`. |
| `pyannote_model` | `pyannote/speaker-diarization-community-1` | Hugging Face model id used with `vad_backend=&quot;pyannote&quot;`. |
| `pyannote_revision` | `None` | Optional Hugging Face model revision. `repo/model@revision` is also accepted. |
| `hf_token` | `None` | Hugging Face token for gated Pyannote models. Falls back to `HF_TOKEN` or `HUGGINGFACE_TOKEN`. |

CLI:

<pre><code>audio-prep chunk \
    --input-dir data/raw_mp3 \
    --output-dir data/chunks \
    --format flac \
    --sample-rate 16000 \
    --min-duration-sec 5 \
    --max-duration-sec 20 \
    --workers 4 \
    --vad-backend silero \
    --profile profiles/chunk-silero.json</code></pre>


Python:

<pre><code>from audio_prep import ChunkConfig

config = ChunkConfig(
    min_duration_sec=5,
    max_duration_sec=20,
    output_format=&quot;flac&quot;,
    sample_rate=16_000,
    num_workers=4,
    vad_backend=&quot;silero&quot;,
)</code></pre>


The CLI sets `--sample-rate 16000` for chunking by default. The Python API
default is `None`, which preserves the source sample rate.

Pyannote comparison:

<pre><code>audio-prep chunk \
    --input-dir data/raw_mp3 \
    --output-dir data/chunks-pyannote \
    --vad-backend pyannote \
    --pyannote-model pyannote/speaker-diarization-community-1 \
    --hf-token "$HF_TOKEN" \
    --profile profiles/chunk-pyannote.json</code></pre>


Python:

<pre><code>from audio_prep import ChunkConfig

config = ChunkConfig(
    sample_rate=16_000,
    vad_backend=&quot;pyannote&quot;,
    pyannote_model=&quot;pyannote/speaker-diarization-community-1&quot;,
)</code></pre>
