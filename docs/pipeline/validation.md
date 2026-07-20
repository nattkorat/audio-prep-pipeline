# Validation

Validation checks converted output before it is accepted into a manifest.

## Checks

`validate_output` checks, in order:

1. The path exists and is a file.
2. The file is not empty.
3. `soundfile` can read the audio header.
4. The sample rate matches `ConversionConfig.sample_rate`.
5. The channel count matches `ConversionConfig.channels`.
6. Duration is at least `ConversionConfig.min_duration_sec`.

Failures return a `ValidationResult` with `valid=False` and a human-readable
reason.

## Duration Probing

`probe_duration` uses FFprobe and can inspect formats that `soundfile` may not
read directly, including MP3.

## Python Example

<pre><code>from pathlib import Path

from audio_prep import ConversionConfig, validate_output

config = ConversionConfig(sample_rate=16_000, channels=1)
result = validate_output(Path(&quot;data/wav16k/clip.wav&quot;), config)

if not result.valid:
    print(result.reason)</code></pre>

