# Manifest API

## `ManifestRecord`

Conversion manifest row.

| Field | Type |
|---|---|
| `source_path` | `str` |
| `output_path` | `Optional[str]` |
| `status` | `str` |
| `duration_sec` | `Optional[float]` |
| `sample_rate` | `Optional[int]` |
| `channels` | `Optional[int]` |
| `error` | `Optional[str]` |

## `ChunkManifestRecord`

Chunk manifest row.

| Field | Type |
|---|---|
| `source_path` | `str` |
| `status` | `str` |
| `num_chunks` | `int` |
| `chunk_paths` | `list[str]` |
| `error` | `Optional[str]` |

## `build_manifest(conversion_results, validation_results)`

Builds conversion manifest records from conversion and validation results.

## `build_chunk_manifest(chunk_results)`

Builds chunk manifest records from chunking results.

## `write_manifest(records, manifest_path)`

Writes any manifest record list to JSONL and creates parent directories.
