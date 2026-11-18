"""由 search_trace 计算轨迹统计（C-TRACE@1/@2）。"""

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


def distinct_scanned(trace: list[SearchProbe]) -> int:
    """按 ``(probe, target)`` 去重后的扫描位置数（C-TRACE@2）。

    ``scanned`` 只取决于抽取器与仓库索引，同一探测项被多条需求各扫一遍时
    扫的是同一批候选，直接累加会让「查过 N 处」随需求条数膨胀。同一键取
    ``max``：``prober`` 用 ``max(scanned, len(hits))`` 收口，取 max 只会
    等于或高于真实扫描量，不会低估。
    """
    best: dict[tuple[str, str], int] = {}
    for probe in trace:
        key = (probe.probe, probe.target)
        if probe.scanned > best.get(key, 0):
            best[key] = probe.scanned
    return sum(best.values())


def headline(trace: list[SearchProbe]) -> str:
    summary = summarize(trace)
    return f"查过 {summary.classes} 类 {summary.scanned_total} 处"