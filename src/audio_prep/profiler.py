"""Lightweight runtime profiling helpers for pipeline runs."""

from __future__ import annotations

import json
import sys
import time
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TypeAlias

JsonPrimitive: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonPrimitive | list["JsonValue"] | dict[str, "JsonValue"]


@dataclass(frozen=True, slots=True)
class _UsageSnapshot:
    user_cpu_sec: float
    system_cpu_sec: float
    max_rss_mb: float


@dataclass(frozen=True, slots=True)
class ProfileRecord:
    """Measured wall time, CPU time, and peak resident memory for one stage."""

    name: str
    elapsed_sec: float
    self_user_cpu_sec: float
    self_system_cpu_sec: float
    children_user_cpu_sec: float
    children_system_cpu_sec: float
    self_max_rss_mb: float
    children_max_rss_mb: float
    started_at: str
    ended_at: str
    metadata: dict[str, JsonPrimitive] = field(default_factory=dict)

    @property
    def total_cpu_sec(self) -> float:
        return (
            self.self_user_cpu_sec
            + self.self_system_cpu_sec
            + self.children_user_cpu_sec
            + self.children_system_cpu_sec
        )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "elapsed_sec": self.elapsed_sec,
            "total_cpu_sec": self.total_cpu_sec,
            "self_user_cpu_sec": self.self_user_cpu_sec,
            "self_system_cpu_sec": self.self_system_cpu_sec,
            "children_user_cpu_sec": self.children_user_cpu_sec,
            "children_system_cpu_sec": self.children_system_cpu_sec,
            "self_max_rss_mb": self.self_max_rss_mb,
            "children_max_rss_mb": self.children_max_rss_mb,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "metadata": dict(self.metadata),
        }


class Profiler:
    """Collect profile records and write them as JSON."""

    def __init__(self) -> None:
        self.records: list[ProfileRecord] = []

    @contextmanager
    def measure(
        self,
        name: str,
        metadata: dict[str, JsonPrimitive] | None = None,
    ) -> Generator[None, None, None]:
        started_at = _utc_now()
        start = time.perf_counter()
        self_start = _get_usage(_ResourceTarget.SELF)
        child_start = _get_usage(_ResourceTarget.CHILDREN)
        failed = False
        error_type: str | None = None
        try:
            yield
        except BaseException as exc:
            failed = True
            error_type = type(exc).__name__
            raise
        finally:
            elapsed = time.perf_counter() - start
            self_end = _get_usage(_ResourceTarget.SELF)
            child_end = _get_usage(_ResourceTarget.CHILDREN)
            record_metadata = dict(metadata or {})
            record_metadata["success"] = not failed
            if error_type is not None:
                record_metadata["error_type"] = error_type
            self.records.append(
                ProfileRecord(
                    name=name,
                    elapsed_sec=elapsed,
                    self_user_cpu_sec=self_end.user_cpu_sec - self_start.user_cpu_sec,
                    self_system_cpu_sec=self_end.system_cpu_sec - self_start.system_cpu_sec,
                    children_user_cpu_sec=child_end.user_cpu_sec - child_start.user_cpu_sec,
                    children_system_cpu_sec=child_end.system_cpu_sec - child_start.system_cpu_sec,
                    self_max_rss_mb=self_end.max_rss_mb,
                    children_max_rss_mb=child_end.max_rss_mb,
                    started_at=started_at,
                    ended_at=_utc_now(),
                    metadata=record_metadata,
                )
            )

    def to_report(
        self,
        operation: str,
        metadata: dict[str, JsonPrimitive] | None = None,
    ) -> dict[str, JsonValue]:
        records: list[JsonValue] = [record.to_dict() for record in self.records]
        summary: dict[str, JsonValue] = {
            "elapsed_sec": sum(record.elapsed_sec for record in self.records),
            "total_cpu_sec": sum(record.total_cpu_sec for record in self.records),
            "self_max_rss_mb": max(
                (record.self_max_rss_mb for record in self.records), default=0.0
            ),
            "children_max_rss_mb": max(
                (record.children_max_rss_mb for record in self.records), default=0.0
            ),
        }
        return {
            "schema_version": 1,
            "operation": operation,
            "generated_at": _utc_now(),
            "metadata": dict(metadata or {}),
            "summary": summary,
            "records": records,
        }

    def write_json(
        self,
        path: Path,
        operation: str,
        metadata: dict[str, JsonPrimitive] | None = None,
    ) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.to_report(operation, metadata), indent=2, sort_keys=True) + "\n"
        )


class _ResourceTarget:
    SELF = "self"
    CHILDREN = "children"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _get_usage(target: str) -> _UsageSnapshot:
    try:
        import resource
    except ImportError:
        return _UsageSnapshot(0.0, 0.0, 0.0)

    who = resource.RUSAGE_SELF if target == _ResourceTarget.SELF else resource.RUSAGE_CHILDREN
    usage = resource.getrusage(who)
    return _UsageSnapshot(
        user_cpu_sec=float(usage.ru_utime),
        system_cpu_sec=float(usage.ru_stime),
        max_rss_mb=_max_rss_to_mb(float(usage.ru_maxrss)),
    )


def _max_rss_to_mb(value: float) -> float:
    if value <= 0:
        return 0.0
    if sys.platform == "darwin":
        return value / (1024 * 1024)
    return value / 1024
