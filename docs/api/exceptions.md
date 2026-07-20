# Exceptions API

## `AudioPrepError`

Base exception for package-specific errors.

## `ConversionError`

Represents a failed FFmpeg conversion. It includes:

- source path
- FFmpeg return code
- stderr text

`convert_file` catches this internally and returns a failed `ConversionResult`.

## `ProbeError`

Raised by `probe_duration` when FFprobe fails or returns an invalid duration.

## `ChunkingError`

Raised internally when VAD chunking cannot produce usable chunks. `chunk_file`
catches it and returns a failed `ChunkResult`.
