# Converter API

## `SUPPORTED_SOURCE_EXTENSIONS`

Tuple of common FFmpeg-readable source extensions discovered by default.

## `DEFAULT_SOURCE_EXTENSIONS`

Alias for the default source extension tuple used by CLI discovery.

## `ConversionResult`

Result dataclass returned by conversion functions.

| Field | Type |
|---|---|
| `source` | `Path` |
| `output` | `Optional[Path]` |
| `success` | `bool` |
| `error` | `Optional[str]` |

## `find_audio_files(input_dir, extensions=DEFAULT_SOURCE_EXTENSIONS)`

Recursively finds source audio files under `input_dir`.

Pass `extensions=None` to return every regular file and let FFmpeg decide
whether each input is decodable.

## `convert_file(source, dest, config)`

Converts one source file to one destination path.

Returns `ConversionResult` instead of raising for file-level failures such as:

- missing source file
- missing FFmpeg binary
- FFmpeg conversion failure
- invalid existing output that cannot be replaced

## `convert_batch(input_dir, output_dir, config=None, source_files=None)`

Converts all discovered or supplied source files and mirrors the input directory
structure under `output_dir`.

Example:

<pre><code>from pathlib import Path

from audio_prep import ConversionConfig, convert_batch

config = ConversionConfig(num_workers=4)
results = convert_batch(
    Path(&quot;data/raw_mp3&quot;),
    Path(&quot;data/wav16k&quot;),
    config,
)</code></pre>
