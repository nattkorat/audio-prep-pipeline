"""Voice-activity-based speech chunking.

Ported from the ASR pretraining-data-prep pipeline. Splits source audio
into speech-only chunks bounded by a [min, max] duration window, so
silence-heavy source recordings don't waste pretraining compute.
Decoding (and resampling, via `ChunkConfig.sample_rate`) is done with
ffmpeg, the same as `converter.py`, so it doesn't depend on `soundfile`
being built with support for every source container.

Silero VAD is the default detector. Pyannote can be selected for comparison,
and the energy detector is available as an offline fallback. Heavy model
imports are deferred to first VAD use so conversion startup stays light.
"""

from __future__ import annotations

import logging
import os
import subprocess
import tempfile
from collections import Counter
from collections.abc import Callable, Iterable
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, TypeAlias, TypeVar, cast

import numpy as np
import soundfile as sf
from numpy.typing import NDArray

from audio_prep.exceptions import AudioPrepError

logger = logging.getLogger(__name__)

SUPPORTED_CHUNK_FORMATS = ("wav", "flac")
SUPPORTED_VAD_BACKENDS = ("silero", "pyannote", "energy")
DEFAULT_PYANNOTE_MODEL = "pyannote/voice-activity-detection"
VadBackend: TypeAlias = Literal["silero", "pyannote", "energy"]

_vad_cache: dict[tuple[str, str | None, bool], tuple[Any, Callable[..., Any]]] = {}
_T = TypeVar("_T")


class ChunkingError(AudioPrepError):
    """Raised when VAD chunking fails to produce usable output."""

    def __init__(self, source: str, reason: str) -> None:
        self.source = source
        self.reason = reason
        super().__init__(f"chunking failed for {source!r}: {reason}")


@dataclass(frozen=True, slots=True)
class ChunkConfig:
    """VAD chunking behavior knobs.

    Kept separate from `ConversionConfig` since chunking has its own notion
    of "duration" (per-chunk, not per-file) and VAD-specific behavior.
    """

    min_duration_sec: float = 5.0
    max_duration_sec: float = 20.0
    output_format: str = "wav"
    sample_rate: int | None = None
    num_workers: int = 1
    overwrite: bool = False
    allow_energy_fallback: bool = False
    vad_backend: str = "silero"
    pyannote_model: str = DEFAULT_PYANNOTE_MODEL
    hf_token: str | None = None

    def __post_init__(self) -> None:
        if self.output_format not in SUPPORTED_CHUNK_FORMATS:
            raise ValueError(
                f"output_format must be one of {SUPPORTED_CHUNK_FORMATS}, "
                f"got {self.output_format!r}"
            )
        if self.min_duration_sec <= 0:
            raise ValueError(f"min_duration_sec must be positive, got {self.min_duration_sec}")
        if self.max_duration_sec < self.min_duration_sec:
            raise ValueError(
                "max_duration_sec must be >= min_duration_sec, got "
                f"{self.max_duration_sec} < {self.min_duration_sec}"
            )
        if self.sample_rate is not None and self.sample_rate <= 0:
            raise ValueError(f"sample_rate must be positive, got {self.sample_rate}")
        if self.num_workers <= 0:
            raise ValueError(f"num_workers must be positive, got {self.num_workers}")
        if self.vad_backend not in SUPPORTED_VAD_BACKENDS:
            raise ValueError(
                f"vad_backend must be one of {SUPPORTED_VAD_BACKENDS}, got {self.vad_backend!r}"
            )
        if self.vad_backend == "pyannote" and not self.pyannote_model.strip():
            raise ValueError("pyannote_model must be non-empty when vad_backend='pyannote'")


@dataclass(slots=True)
class ChunkResult:
    """Outcome of chunking a single source file."""

    source: Path
    chunks: list[Path]
    success: bool
    error: str | None = None


def _load_vad_from_package() -> tuple[Any, Callable[..., Any]]:
    from silero_vad import get_speech_timestamps, load_silero_vad

    model = load_silero_vad()

    def detect(audio: Any, sampling_rate: int) -> Any:
        return get_speech_timestamps(audio, model, sampling_rate=sampling_rate)

    return model, detect


def _load_vad_from_torch_hub() -> tuple[Any, Callable[..., Any]]:
    import torch

    torch.hub.set_dir(os.path.expanduser("~/.cache/torch/hub"))

    with torch.no_grad():
        hub_load: Callable[..., Any] = torch.hub.load
        model, utils = hub_load(
            repo_or_dir="snakers4/silero-vad",
            model="silero_vad",
            trust_repo=True,
            force_reload=False,
            verbose=False,
        )
    get_speech_timestamps = utils[0]

    def detect(audio: Any, sampling_rate: int) -> Any:
        return get_speech_timestamps(audio, model, sampling_rate=sampling_rate)

    return model, detect


def _load_vad_from_pyannote(
    model_name: str,
    hf_token: str | None,
) -> tuple[Any, Callable[..., Any]]:
    import torch
    from pyannote.audio import Pipeline

    from_pretrained: Callable[..., Any] = Pipeline.from_pretrained
    kwargs = {"token": hf_token} if hf_token else {}
    try:
        pipeline_model = from_pretrained(model_name, **kwargs)
    except TypeError:
        if not hf_token:
            raise
        pipeline_model = from_pretrained(model_name, use_auth_token=hf_token)
    if pipeline_model is None:
        raise RuntimeError(
            f"pyannote.audio could not load {model_name!r}; check model access and token"
        )
    pipeline = cast(Callable[[dict[str, Any]], Any], pipeline_model)

    def detect(audio: Any, sampling_rate: int) -> list[dict[str, int]]:
        waveform = torch.as_tensor(np.asarray(audio), dtype=torch.float32)
        if waveform.ndim == 1:
            waveform = waveform.unsqueeze(0)
        with torch.no_grad():
            output = pipeline({"waveform": waveform, "sample_rate": sampling_rate})
        return _pyannote_output_to_timestamps(output, sampling_rate)

    return pipeline_model, detect


def _pyannote_output_to_timestamps(output: Any, sampling_rate: int) -> list[dict[str, int]]:
    if hasattr(output, "get_timeline"):
        timeline = output.get_timeline().support()
    elif hasattr(output, "support"):
        timeline = output.support()
    else:
        raise RuntimeError("pyannote VAD output does not expose a timeline")

    timestamps: list[dict[str, int]] = []
    for segment in timeline:
        start = max(0, int(float(segment.start) * sampling_rate))
        end = max(start, int(float(segment.end) * sampling_rate))
        if end > start:
            timestamps.append({"start": start, "end": end})
    return timestamps


def _with_progress(iterable: Iterable[_T], **kwargs: Any) -> Iterable[_T]:
    try:
        from tqdm import tqdm
    except ImportError:
        return iterable
    return cast(Iterable[_T], tqdm(iterable, **kwargs))


def _energy_based_detector(audio: NDArray[Any], sampling_rate: int) -> list[dict[str, int]]:
    """Simple RMS-energy VAD fallback for environments without Silero access.

    Lower quality than Silero -- only intended as a last resort so a
    pipeline run can still produce *something* offline.
    """
    frame_size = int(0.02 * sampling_rate)
    if frame_size <= 0 or len(audio) < frame_size:
        return []

    frames = np.array(
        [
            np.sqrt(np.mean(audio[i : i + frame_size] ** 2))
            for i in range(0, len(audio) - frame_size, frame_size)
        ]
    )
    if frames.size == 0:
        return []

    threshold = frames.mean() * 0.5
    speech_frames = frames > threshold

    timestamps: list[dict[str, int]] = []
    in_speech = False
    start = 0
    for i, is_speech in enumerate(speech_frames):
        if is_speech and not in_speech:
            start = i * frame_size
            in_speech = True
        elif not is_speech and in_speech:
            timestamps.append({"start": start, "end": i * frame_size})
            in_speech = False
    if in_speech:
        timestamps.append({"start": start, "end": len(audio)})
    return timestamps


def load_vad_model(
    allow_energy_fallback: bool = False,
    *,
    backend: str = "silero",
    pyannote_model: str = DEFAULT_PYANNOTE_MODEL,
    hf_token: str | None = None,
) -> tuple[Any, Callable[..., Any]]:
    """Load (and process-wide cache) a VAD speech-timestamp detector.

    For `backend="silero"`, tries the `silero-vad` pip package first, then
    `torch.hub`. For `backend="pyannote"`, loads `pyannote_model` through
    `pyannote.audio.Pipeline.from_pretrained`. Returns `(model, detect)` where
    `detect(audio, sampling_rate)` returns a list of `{"start": int, "end": int}`
    sample-index dicts. `model` is `None` when running the energy detector.

    Raises `ChunkingError` if the selected VAD backend can't be loaded and
    `allow_energy_fallback` is `False`.
    """
    if backend not in SUPPORTED_VAD_BACKENDS:
        raise ValueError(f"backend must be one of {SUPPORTED_VAD_BACKENDS}, got {backend!r}")

    resolved_token = hf_token or os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN")
    model_key = pyannote_model if backend == "pyannote" else None
    token_present = bool(resolved_token) if backend == "pyannote" else False
    cache_key = (backend, model_key, token_present)
    if cache_key in _vad_cache:
        return _vad_cache[cache_key]

    if backend == "energy":
        _vad_cache[cache_key] = (None, _energy_based_detector)
        return _vad_cache[cache_key]

    errors = []
    model: Any = None
    detect: Callable[..., Any] | None = None

    if backend == "silero":
        for name, loader in (
            ("silero-vad package", _load_vad_from_package),
            ("torch.hub", _load_vad_from_torch_hub),
        ):
            try:
                model, detect = loader()
                break
            except Exception as exc:  # noqa: BLE001 - try the next loader, report all failures
                errors.append(f"{name}: {exc}")
    elif backend == "pyannote":
        try:
            model, detect = _load_vad_from_pyannote(pyannote_model, resolved_token)
        except Exception as exc:  # noqa: BLE001 - surface optional backend load errors clearly
            errors.append(f"pyannote.audio model {pyannote_model!r}: {exc}")

    if detect is None:
        if not allow_energy_fallback:
            raise ChunkingError(
                "<vad model>",
                f"could not load VAD backend {backend!r}, and allow_energy_fallback "
                "is disabled. "
                f"Underlying errors: {'; '.join(errors)}",
            )
        logger.warning(
            "Falling back to low-quality energy-based VAD (%s unavailable): %s",
            backend,
            "; ".join(errors),
        )
        model, detect = None, _energy_based_detector

    _vad_cache[cache_key] = (model, detect)
    return _vad_cache[cache_key]


def chunk_audio_with_vad(
    audio: NDArray[Any],
    sr: int,
    config: ChunkConfig | None = None,
    detect: Callable[..., Any] | None = None,
) -> list[dict[str, Any]]:
    """Split `audio` into speech-only chunks bounded by `config`'s duration window.

    Pass `detect` (a `(audio, sampling_rate) -> [{"start", "end"}, ...]`
    callable) to reuse an already-loaded model across files -- see
    `chunk_batch` -- or to inject a fake detector in tests. When omitted,
    a VAD model is loaded (and cached) automatically.

    Returns a list of `{"audio": np.ndarray, "start": int, "end": int,
    "duration": float}` dicts, one per chunk.
    """
    config = config or ChunkConfig()

    if detect is None:
        _, detect = load_vad_model(
            allow_energy_fallback=config.allow_energy_fallback,
            backend=config.vad_backend,
            pyannote_model=config.pyannote_model,
            hf_token=config.hf_token,
        )

    audio = np.asarray(audio)
    if audio.ndim > 1:
        audio = np.mean(audio, axis=-1)
    audio = audio.astype(np.float32, copy=False)

    speech_timestamps = detect(audio, sampling_rate=sr)

    max_samples = int(config.max_duration_sec * sr)
    chunks: list[dict[str, Any]] = []
    for timestamp in speech_timestamps:
        segment_start, segment_end = timestamp["start"], timestamp["end"]
        current_start = segment_start
        while current_start < segment_end:
            current_end = min(current_start + max_samples, segment_end)
            duration = (current_end - current_start) / sr
            if duration >= config.min_duration_sec:
                chunks.append(
                    {
                        "audio": audio[current_start:current_end],
                        "start": current_start,
                        "end": current_end,
                        "duration": duration,
                    }
                )
            current_start = current_end
    return chunks


_SOUNDFILE_NATIVE_EXTENSIONS = {".wav", ".flac"}


def _decode_via_ffmpeg(source: Path, target_sr: int | None) -> tuple[NDArray[Any], int]:
    """Decode `source` (mono) via ffmpeg, resampling to `target_sr` if given.

    Reuses ffmpeg rather than a pure-Python decoder/resampler for the same
    reason `converter.py` shells out to it: it's the most robust option
    across real-world source files (MP3 VBR/odd headers/ID3 variants
    included), and it's already a required system dependency for this
    project -- unlike MP3 support in `soundfile`, which depends on the
    `libsndfile` build installed.
    """
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(source)]
        if target_sr is not None:
            cmd += ["-ar", str(target_sr)]
        cmd += ["-ac", "1", "-f", "wav", "-c:a", "pcm_s16le", str(tmp_path)]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            raise RuntimeError(f"ffmpeg decode of {source} failed: {proc.stderr.strip()}")
        audio, sr = sf.read(str(tmp_path), dtype="float32", always_2d=False)
        return audio, sr
    finally:
        tmp_path.unlink(missing_ok=True)


def _read_audio_for_chunking(source: Path, target_sr: int | None) -> tuple[NDArray[Any], int]:
    """Read `source`, decoding/resampling via ffmpeg where needed.

    Only reads directly through `soundfile` (skipping the ffmpeg
    round-trip) for its native WAV/FLAC formats, and only when no
    `target_sr` is requested or the file is already at that rate.
    Anything else (MP3 in particular) always goes through ffmpeg.
    """
    if source.suffix.lower() not in _SOUNDFILE_NATIVE_EXTENSIONS:
        return _decode_via_ffmpeg(source, target_sr)
    if target_sr is not None and sf.info(str(source)).samplerate != target_sr:
        return _decode_via_ffmpeg(source, target_sr)
    audio, sr = sf.read(str(source), dtype="float32", always_2d=False)
    return audio, sr


def _is_valid_existing_chunk(path: Path, expected_sr: int) -> bool:
    try:
        info = sf.info(str(path))
    except Exception:  # noqa: BLE001 - any backend decode failure means "not a valid chunk"
        return False
    return bool(info.samplerate == expected_sr and info.frames > 0)


def _write_chunks(
    chunks: list[dict[str, Any]],
    source: Path,
    output_dir: Path,
    sr: int,
    config: ChunkConfig,
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for i, chunk in enumerate(chunks, start=1):
        chunk_path = output_dir / f"{source.stem}_chunk_{i}.{config.output_format}"
        if (
            not config.overwrite
            and chunk_path.exists()
            and _is_valid_existing_chunk(chunk_path, sr)
        ):
            written.append(chunk_path)
            continue
        sf.write(str(chunk_path), chunk["audio"], sr, format=config.output_format.upper())
        written.append(chunk_path)
    return written


def chunk_file(
    source: Path,
    output_dir: Path,
    config: ChunkConfig | None = None,
    detect: Callable[..., Any] | None = None,
) -> ChunkResult:
    """Chunk a single source audio file (MP3, WAV, or FLAC) into speech segments.

    Returns a `ChunkResult` rather than raising on failure so batch runs
    can collect partial results instead of aborting on the first bad or
    silent file in a large corpus.
    """
    config = config or ChunkConfig()
    source = Path(source)
    output_dir = Path(output_dir)

    if not source.is_file():
        return ChunkResult(source, [], success=False, error=f"source not found: {source}")

    try:
        audio, sr = _read_audio_for_chunking(source, config.sample_rate)
    except Exception as exc:  # noqa: BLE001 - surface any backend decode/resample failure as a failed result
        return ChunkResult(source, [], success=False, error=f"could not read {source}: {exc}")

    try:
        chunks = chunk_audio_with_vad(audio, sr, config, detect=detect)
    except ChunkingError as exc:
        return ChunkResult(source, [], success=False, error=str(exc))

    if not chunks:
        return ChunkResult(
            source,
            [],
            success=False,
            error="no speech chunks detected (silent input, or shorter than min_duration_sec)",
        )

    written = _write_chunks(chunks, source, output_dir, sr, config)
    return ChunkResult(source, written, success=True, error=None)


def chunk_batch(
    input_dir: Path,
    output_dir: Path,
    config: ChunkConfig | None = None,
    source_files: list[Path] | None = None,
    extensions: tuple[str, ...] | None = None,
) -> list[ChunkResult]:
    """Chunk source audio under `input_dir` directly (no separate `convert` step needed).

    Mirrors the input directory's relative subfolder structure, same as
    `converter.convert_batch`. The VAD model is loaded once up front (and
    cached per-process) rather than reloading it for every file.

    Pass `source_files` to chunk a pre-filtered list instead of
    re-discovering files under `input_dir` (useful for tests, and for
    unusual source formats -- `chunk_file` itself doesn't care about source
    extension, it just decodes whatever path it's given). Pass
    `extensions=None` to use the converter module's default source extension
    set; pass `source_files` for exact control.
    """
    config = config or ChunkConfig()
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)

    if source_files is None:
        from audio_prep.converter import DEFAULT_SOURCE_EXTENSIONS, find_audio_files

        source_files = find_audio_files(
            input_dir, DEFAULT_SOURCE_EXTENSIONS if extensions is None else extensions
        )

    if not source_files:
        logger.warning("No source audio files found under %s", input_dir)
        return []

    # Warm the cache in the parent process so a sequential run (and each
    # worker's first call, via the same module-level cache) doesn't pay
    # the load cost per file. Also lets a load failure surface immediately,
    # before any progress bar work, with its exact underlying error.
    _model, detect = load_vad_model(
        allow_energy_fallback=config.allow_energy_fallback,
        backend=config.vad_backend,
        pyannote_model=config.pyannote_model,
        hf_token=config.hf_token,
    )

    jobs = []
    for f in source_files:
        rel_dir = f.parent.relative_to(input_dir) if f.is_relative_to(input_dir) else Path()
        jobs.append((f, output_dir / rel_dir))

    chunk_keys = Counter((dst, src.stem) for src, dst in jobs)
    jobs = [
        (
            src,
            dst / f"{src.stem}_{src.suffix.lower().lstrip('.') or 'no_ext'}"
            if chunk_keys[(dst, src.stem)] > 1
            else dst,
        )
        for src, dst in jobs
    ]

    if config.num_workers == 1:
        return [
            chunk_file(src, dst, config, detect=detect)
            for src, dst in _with_progress(jobs, desc="Chunking", unit="file")
        ]

    results: list[ChunkResult] = []
    with ProcessPoolExecutor(max_workers=config.num_workers) as pool:
        futures = {pool.submit(chunk_file, src, dst, config): src for src, dst in jobs}
        for future in _with_progress(
            as_completed(futures), total=len(futures), desc="Chunking", unit="file"
        ):
            results.append(future.result())

    order = {src: i for i, (src, _dst) in enumerate(jobs)}
    results.sort(key=lambda r: order[r.source])
    return results
