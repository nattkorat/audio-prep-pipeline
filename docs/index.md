# Audio Prep Pipeline

Welcome to the Audio Prep Pipeline documentation.

This project converts raw audio recordings into datasets ready for
self-supervised speech pretraining such as Wav2Vec2 and XLS-R.

The pipeline performs four major stages:

1. Audio discovery
2. Audio conversion
3. Validation
4. Manifest generation

The default output is:

- WAV
- 16 kHz
- Mono

which matches the expected input specification of most modern SSL speech
models.

## Pipeline Overview


`Raw MP3` -> `Find audio files` -> `Convert using FFmpeg` -> `Validate output`-> `Generate JSONL manifest` -> `Ready for pretraining`


## Features
- Multi-process conversion
- Automatic validation
- FFmpeg backend
- JSONL manifest generation
- Failure recovery
- Modular Python API
- CLI interface
- Unit tested\

> [Getting Started](getting-started.md) <
