# Manifest

Manifests are JSONL files. Each line is one JSON object.

## Conversion Manifest

`build_manifest` combines conversion results and validation results.

Fields:

| Field | Type | Meaning |
|---|---|---|
| `source_path` | string | Original source file path. |
| `output_path` | string or null | Converted output path, when available. |
| `status` | string | `ok`, `conversion_failed`, or `validation_failed`. |
| `duration_sec` | number or null | Validated duration. |
| `sample_rate` | number or null | Validated sample rate. |
| `channels` | number or null | Validated channel count. |
| `error` | string or null | Error or validation reason. |

Example:

<pre><code>{&quot;source_path&quot;:&quot;data/raw_mp3/a.mp3&quot;,&quot;output_path&quot;:&quot;data/wav16k/a.wav&quot;,&quot;status&quot;:&quot;ok&quot;,&quot;duration_sec&quot;:1.0,&quot;sample_rate&quot;:16000,&quot;channels&quot;:1,&quot;error&quot;:null}</code></pre>


## Chunk Manifest

`build_chunk_manifest` records one row per source file.

Fields:

| Field | Type | Meaning |
|---|---|---|
| `source_path` | string | Original source file path. |
| `status` | string | `ok` or `chunking_failed`. |
| `num_chunks` | number | Number of chunks written. |
| `chunk_paths` | list[string] | Written chunk paths. |
| `error` | string or null | Chunking error, when any. |

## Writing Manifests

CLI:

<pre><code>audio-prep convert \
    --input-dir data/raw_mp3 \
    --output-dir data/wav16k \
    --manifest data/manifest.jsonl

audio-prep chunk \
    --input-dir data/raw_mp3 \
    --output-dir data/chunks \
    --manifest data/chunk_manifest.jsonl</code></pre>


Python:

Use `write_manifest` for both conversion and chunk records:

<pre><code>from audio_prep.manifest import write_manifest

write_manifest(records, &quot;data/manifest.jsonl&quot;)</code></pre>


Parent directories are created automatically.
