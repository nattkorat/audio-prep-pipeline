# Profiler API

## `Profiler`

Collects profile records and writes a JSON report.

<pre><code>from pathlib import Path

from audio_prep import Profiler

profiler = Profiler()

with profiler.measure(&quot;stage-name&quot;, {&quot;files&quot;: 10}):
    ...

profiler.write_json(
    Path(&quot;profiles/run.json&quot;),
    operation=&quot;chunk&quot;,
    metadata={&quot;vad_backend&quot;: &quot;silero&quot;},
)</code></pre>


## `ProfileRecord`

| Field | Type |
|---|---|
| `name` | `str` |
| `elapsed_sec` | `float` |
| `total_cpu_sec` | `float` |
| `self_user_cpu_sec` | `float` |
| `self_system_cpu_sec` | `float` |
| `children_user_cpu_sec` | `float` |
| `children_system_cpu_sec` | `float` |
| `self_max_rss_mb` | `float` |
| `children_max_rss_mb` | `float` |
| `started_at` | `str` |
| `ended_at` | `str` |
| `metadata` | `dict[str, JsonPrimitive]` |
