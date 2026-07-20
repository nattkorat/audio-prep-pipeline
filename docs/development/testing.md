# Testing

The test suite uses generated audio fixtures instead of checked-in binary audio.
Synthetic MP3 and WAV files are created with FFmpeg during tests.

## Run Tests

<pre><code>make test</code></pre>


or:

<pre><code>PYTHONPATH=src pytest</code></pre>


## Run Focused Tests

<pre><code>PYTHONPATH=src pytest tests/test_converter.py
PYTHONPATH=src pytest tests/test_chunker.py</code></pre>


## Lint And Typecheck

<pre><code>make lint
make typecheck</code></pre>


## Full Local Check

<pre><code>make check</code></pre>


## Build Documentation

<pre><code>make docs</code></pre>


For live preview:

<pre><code>make docs-serve</code></pre>


## Notes

Some tests exercise `ProcessPoolExecutor`. In restricted environments, these may
need normal OS semaphore access.
