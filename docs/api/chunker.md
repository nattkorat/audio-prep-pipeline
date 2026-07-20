# Chunker API

## `ChunkConfig`

Configuration dataclass for VAD chunking.

| Field | Type | Default |
|---|---|---:|
| `min_duration_sec` | `float` | `5.0` |
| `max_duration_sec` | `float` | `20.0` |
| `output_format` | `str` | `wav` |
| `sample_rate` | `Optional[int]` | `None` |
| `num_workers` | `int` | `1` |
| `overwrite` | `bool` | `False` |
| `allow_energy_fallback` | `bool` | `False` |

## `ChunkResult`

| Field | Type |
|---|---|
| `source` | `Path` |
| `chunks` | `list[Path]` |
| `success` | `bool` |
| `error` | `Optional[str]` |

## `chunk_file(source, output_dir, config=None, detect=None)`

Chunks one source file. The optional `detect` argument is primarily useful for
tests or custom VAD implementations.

## `chunk_batch(input_dir, output_dir, config=None, source_files=None)`

Discovers supported source audio files under `input_dir` unless `source_files` is supplied, then
chunks each file.

Example:

<pre><code>from pathlib import Path

from audio_prep import ChunkConfig, chunk_batch

config = ChunkConfig(min_duration_sec=5, max_duration_sec=20, sample_rate=16_000)
results = chunk_batch(Path(&quot;data/raw_mp3&quot;), Path(&quot;data/chunks&quot;), config)</code></pre>
