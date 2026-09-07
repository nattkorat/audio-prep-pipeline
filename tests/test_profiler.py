from __future__ import annotations

import json
from pathlib import Path

from audio_prep.profiler import Profiler


def test_profiler_records_stage_and_writes_report(tmp_path: Path) -> None:
    profiler = Profiler()

    with profiler.measure("stage", {"files": 2}):
        sum(range(100))

    report_path = tmp_path / "profile.json"
    profiler.write_json(report_path, operation="convert", metadata={"exit_code": 0})

    report = json.loads(report_path.read_text())
    assert report["operation"] == "convert"
    assert report["metadata"]["exit_code"] == 0
    assert report["summary"]["elapsed_sec"] >= 0
    assert report["records"][0]["name"] == "stage"
    assert report["records"][0]["metadata"]["files"] == 2
    assert report["records"][0]["metadata"]["success"] is True
