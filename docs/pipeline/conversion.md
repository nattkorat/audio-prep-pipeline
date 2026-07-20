# Conversion

Conversion is handled by FFmpeg through `convert_file` and `convert_batch`.

## Output Path Rules

For batch conversion, the output path is derived from the source path relative
to `input_dir`:

<pre><code>data/raw_mp3/speaker_a/clip_001.mp3</code></pre>


converted to WAV under `data/wav16k` becomes:

<pre><code>data/wav16k/speaker_a/clip_001.wav</code></pre>


If two source files in the same directory would produce the same output path,
the original source extension is added to the output stem. For example,
`clip.mp3` and `clip.wav` become `clip_mp3.wav` and `clip_wav.wav`.

## FFmpeg Settings

The converter always sets:

- `-ar` to the configured sample rate
- `-ac` to the configured channel count
- WAV output as signed 16-bit PCM
- FLAC output with the FLAC muxer

When `normalize_loudness=True`, FFmpeg also receives:

<pre><code>loudnorm=I=-23:LRA=7:TP=-2</code></pre>


## Resume Behavior

When `overwrite=False`, an existing output is reused only if it passes
validation for the current target spec. Invalid existing outputs are removed and
converted again.

If an invalid existing output cannot be removed, the file is reported as a
failed `ConversionResult` instead of raising out of the batch.

## Batch Behavior

`convert_batch` uses a process pool when `num_workers > 1`. Results are sorted
back into discovery order before being returned.

Bad source files do not stop the run. They return `ConversionResult` objects
with `success=False` and an error message.
