"""artifact 抽取器：结果/产物文件里的测量痕迹（C-EXTRACTOR@4）。

测量结果常写在 ``bench.log`` / ``result.csv`` 一类产物里，``bench`` 抽取器只看代码与
配置后缀，因此这里单独覆盖"产物文件"。

``kind`` 必须是 ``bench``：``matcher`` 的 ``_ABILITY_TYPES`` 分支靠"有没有 bench 证据"
区分"有测量"与"有配置，无测量"。``strength=medium``：脚本可复跑，日志只是单次快照。
"""

from __future__ import annotations

from ..index import RepoIndex
from ..schema import ClaimType, Evidence, EvidenceKind, Strength
from . import SOURCE_LIMIT, _evidence, _line_text

SUFFIXES = frozenset({".log", ".csv", ".json", ".txt", ".xml", ".html"})
NAME_HINTS = ("result", "bench", "loadtest", "perf", "report", "coverage")
MEASURE_WORDS = (
    "p95",
    "p99",
    "latency",
    "qps",
    "rps",
    "throughput",
    "error rate",
    "错误率",
    "users",
    "并发",
    "t_total",
    "coverage",
)
CAP = 40
SUPPORTS = [ClaimType.performance, ClaimType.concurrency, ClaimType.testing]


def _in_scope(p) -> bool:
    suffix = p.suffix.lower()
    if suffix == ".md":
        return False
    if suffix in SUFFIXES:
        return True
    lowered = p.name.lower()
    return any(hint in lowered for hint in NAME_HINTS)


def _is_measurement(text: str) -> bool:
    lowered = text.lower()
    return any(word in lowered for word in MEASURE_WORDS) and any(ch.isdigit() for ch in text)


def extract(index: RepoIndex) -> list[Evidence]:
    out: list[Evidence] = []
    seen: set[tuple[str, int]] = set()

    for p in index.files:
        if not _in_scope(p):
            continue
        rel = index.rel(p)
        for raw in index.read(p, limit=SOURCE_LIMIT).splitlines():
            candidate = raw.strip()
            if not candidate or not _is_measurement(candidate):
                continue
            line = index.line_of(p, candidate)
            if line is None or (rel, line) in seen:
                continue
            snippet = _line_text(index, p, line)
            if not _is_measurement(snippet):
                continue
            seen.add((rel, line))
            if len(out) >= CAP:
                return out
            out.append(
                _evidence(
                    "artifact",
                    len(out) + 1,
                    EvidenceKind.bench,
                    rel,
                    line,
                    snippet,
                    SUPPORTS,
                    Strength.medium,
                )
            )

    return out