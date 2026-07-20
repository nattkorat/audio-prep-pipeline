# Discovery

Discovery is handled by `find_audio_files`.

## Behavior

- Recursively walks the input directory.
- Selects files by extension.
- Matches extensions case-insensitively.
- Returns sorted paths for deterministic runs.
- Raises `FileNotFoundError` when the input directory does not exist.

The default extension set includes common FFmpeg-readable audio/video containers
such as:

<pre><code>(".mp3", ".wav", ".flac", ".m4a", ".ogg", ".opus", ".webm", ".mp4", ...)</code></pre>


## Python Example

<pre><code>from pathlib import Path

from audio_prep import find_audio_files

files = find_audio_files(Path(&quot;data/raw_mp3&quot;))</code></pre>


## Custom Extensions

The function accepts a custom extension tuple:

<pre><code>files = find_audio_files(
    Path(&quot;data/audio&quot;),
    extensions=(&quot;.mp3&quot;, &quot;.m4a&quot;, &quot;.ogg&quot;),
)</code></pre>


Pass `extensions=None` to return every regular file and let FFmpeg decide what
can be decoded:

<pre><code>files = find_audio_files(Path("data/mixed"), extensions=None)</code></pre>

## CLI Example

The CLI exposes the same behavior with `--extensions`:

<pre><code>audio-prep convert \
    --input-dir data/audio \
    --output-dir data/wav16k \
    --extensions mp3,m4a,ogg

audio-prep chunk \
    --input-dir data/mixed \
    --output-dir data/chunks \
    --extensions all</code></pre>


Use `--extensions all` to scan every regular file.
