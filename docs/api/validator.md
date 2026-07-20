# Validator API

## `ValidationResult`

| Field | Type |
|---|---|
| `path` | `Path` |
| `valid` | `bool` |
| `duration_sec` | `Optional[float]` |
| `sample_rate` | `Optional[int]` |
| `channels` | `Optional[int]` |
| `reason` | `Optional[str]` |

## `validate_output(path, config)`

Validates a converted output file against `ConversionConfig`.

Example:

<pre><code>from pathlib import Path

from audio_prep import ConversionConfig, validate_output

result = validate_output(Path(&quot;data/wav16k/a.wav&quot;), ConversionConfig())</code></pre>


## `probe_duration(path)`

Uses FFprobe to return duration in seconds. Raises `ProbeError` when FFprobe
fails or returns an unparseable duration.
