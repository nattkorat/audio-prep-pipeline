# Architecture

The package is intentionally small and module-oriented.

<pre><code>audio_prep/
├── cli.py          # argparse entry point
├── config.py       # conversion configuration
├── converter.py    # discovery and FFmpeg conversion
├── chunker.py      # VAD chunking
├── profiler.py     # runtime resource profiles
├── validator.py    # output validation and duration probing
├── manifest.py     # JSONL manifest records and writer
└── exceptions.py   # package exceptions</code></pre>


## Design Choices

## FFmpeg For Decode And Encode

Source decoding is delegated to FFmpeg because real corpora often contain VBR
files, odd headers, unusual containers, corrupt metadata, and other cases that
pure Python decoders handle less consistently.

## Result Objects Instead Of Batch Exceptions

Conversion and chunking return result objects per file. This lets a large corpus
finish even when individual files are broken.

## Validation After Conversion

FFmpeg success is not treated as enough. Converted output is reopened and
checked for sample rate, channel count, readability, and minimum duration.

## Chunking Dependencies

The base package includes Torch, Silero VAD, Pyannote, and tqdm so both
`convert` and `chunk` are ready after `pip install audio-prep-pipeline`.
Chunker imports are still lazy, so conversion-only commands avoid VAD startup
cost.

## Profiling

The profiler uses the standard library to record wall time, CPU time, child
process CPU time, and peak RSS. CLI reports are JSON so model-backend timing
runs can be compared outside the package.
