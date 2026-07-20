# Config API

## `ConversionConfig`

<pre><code>from audio_prep import ConversionConfig</code></pre>


Immutable dataclass for conversion and validation settings.

Fields:

| Field | Type | Default |
|---|---|---:|
| `output_format` | `str` | `wav` |
| `sample_rate` | `int` | `16000` |
| `channels` | `int` | `1` |
| `num_workers` | `int` | `4` |
| `min_duration_sec` | `float` | `0.5` |
| `overwrite` | `bool` | `False` |
| `normalize_loudness` | `bool` | `False` |

Supported formats are `wav` and `flac`. Invalid numeric values raise
`ValueError`.
