"""audio_prep: convert source audio into pretraining-ready WAV/FLAC.

Pipeline stages:
    1. discovery   - find source audio files under an input directory
    2. conversion  - decode + resample + remix to a target WAV/FLAC spec
    3. validation  - sanity-check converted output (sample rate, duration, integrity)
    4. chunking    - split into speech-focused chunks via VAD
    5. manifest    - emit a JSONL manifest describing the resulting dataset
"""

from audio_prep.chunker import (
    DEFAULT_PYANNOTE_MODEL,
    SUPPORTED_VAD_BACKENDS,
    ChunkConfig,
    ChunkingError,
    ChunkResult,
    chunk_batch,
    chunk_file,
    load_vad_model,
)
from audio_prep.config import ConversionConfig
from audio_prep.converter import (
    DEFAULT_SOURCE_EXTENSIONS,
    SUPPORTED_SOURCE_EXTENSIONS,
    ConversionResult,
    convert_batch,
    convert_file,
    find_audio_files,
)
from audio_prep.exceptions import AudioPrepError, ConversionError, ProbeError
from audio_prep.manifest import (
    ChunkManifestRecord,
    ManifestRecord,
    build_chunk_manifest,
    build_manifest,
    write_manifest,
)
from audio_prep.profiler import Profiler, ProfileRecord
from audio_prep.validator import ValidationResult, validate_output

__version__ = "0.1.7"

__all__ = [
    "ConversionConfig",
    "ConversionResult",
    "SUPPORTED_SOURCE_EXTENSIONS",
    "DEFAULT_SOURCE_EXTENSIONS",
    "convert_batch",
    "convert_file",
    "find_audio_files",
    "AudioPrepError",
    "ConversionError",
    "ProbeError",
    "ManifestRecord",
    "ChunkManifestRecord",
    "build_manifest",
    "build_chunk_manifest",
    "write_manifest",
    "ValidationResult",
    "validate_output",
    "ChunkConfig",
    "ChunkResult",
    "ChunkingError",
    "SUPPORTED_VAD_BACKENDS",
    "DEFAULT_PYANNOTE_MODEL",
    "load_vad_model",
    "chunk_batch",
    "chunk_file",
    "ProfileRecord",
    "Profiler",
]
