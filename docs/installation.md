# Installation

## Requirements

- Python 3.10 or newer
- FFmpeg and FFprobe available on `PATH`
- `libsndfile`, usually installed automatically with `soundfile` wheels on
  common platforms

## Install FFmpeg

macOS:

<pre><code>brew install ffmpeg</code></pre>


Ubuntu or Debian:

<pre><code>sudo apt-get update
sudo apt-get install ffmpeg</code></pre>


Check that both binaries are available:

<pre><code>ffmpeg -version
ffprobe -version</code></pre>


## Install The Package

For local development:

<pre><code>make install</code></pre>


This runs:

<pre><code>pip install -e &quot;.[dev]&quot;
pre-commit install</code></pre>


For installation from PyPI:

<pre><code>pip install audio-prep-pipeline</code></pre>


Install directly from GitHub:

<pre><code>pip install &quot;audio-prep-pipeline @ git+https://github.com/nattkorat/audio-prep-pipeline.git&quot;</code></pre>


For editable local usage without developer tools:

<pre><code>pip install -e .</code></pre>


For documentation work:

<pre><code>pip install -e &quot;.[docs]&quot;</code></pre>


## Chunking Dependencies

The standard package install includes `torch`, `silero-vad`, and `tqdm`, so
both `audio-prep convert` and `audio-prep chunk` are ready after:

<pre><code>pip install audio-prep-pipeline</code></pre>


The first chunking run loads Silero from the installed `silero-vad` package.
If Silero cannot load in an offline environment, pass `--allow-energy-fallback`
to use the lower-quality offline energy detector.
