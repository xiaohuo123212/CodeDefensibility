"""由 search_trace 计算轨迹统计（C-TRACE@1）。"""

from __future__ import annotations

from dataclasses import dataclass

from .schema import SearchProbe


@dataclass(frozen=True)
class TraceSummary:
    classes: int
    scanned_total: int
    hits_total: int
    where: list[str]


def summarize(trace: list[SearchProbe]) -> TraceSummary:
    where: list[str] = []
    seen: set[str] = set()
    for probe in trace:
        for item in probe.where:
            if item not in seen:
                seen.add(item)
                where.append(item)

    return TraceSummary(
        classes=len(trace),
        scanned_total=sum(p.scanned for p in trace),
        hits_total=sum(p.hits for p in trace),
        where=where,
    )


def headline(trace: list[SearchProbe]) -> str:
    summary = summarize(trace)
    return f"查过 {summary.classes} 类 {summary.scanned_total} 处"