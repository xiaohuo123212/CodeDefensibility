"""bench 抽取器：压测/基准脚本与测量痕迹。"""

from __future__ import annotations

from ..index import RepoIndex
from ..schema import ClaimType, Evidence, EvidenceKind, Strength
from . import SCAN_SUFFIXES, _evidence, _line_text

SUPPORTS = [ClaimType.performance, ClaimType.concurrency]
CAP = 40
NAME_HINTS = ("locustfile", "locust", "k6", "jmeter", "wrk", "benchmark", "timeit")
CONTENT_NEEDLES = (
    "locustfile",
    "locust",
    "k6",
    "jmeter",
    "wrk",
    "ab -n",
    "benchmark",
    "timeit",
    "pytest-benchmark",
)


def extract(index: RepoIndex) -> list[Evidence]:
    out: list[Evidence] = []
    seen: set[tuple[str, int, str]] = set()

    def add(rel: str, line: int, snippet: str, tag: str) -> None:
        if len(out) >= CAP:
            return
        key = (rel, line, tag)
        if key in seen:
            return
        seen.add(key)
        out.append(
            _evidence(
                "bench",
                len(out) + 1,
                EvidenceKind.bench,
                rel,
                line,
                snippet,
                SUPPORTS,
                Strength.high,
            )
        )

    for p in index.files:
        rel = index.rel(p)
        lowered = rel.lower()
        for hint in NAME_HINTS:
            if hint not in lowered:
                continue
            line = index.line_of(p, hint)
            if line is None:
                break
            text = _line_text(index, p, line)
            if hint in text:
                add(rel, line, text, hint)
            break

        if p.suffix.lower() not in SCAN_SUFFIXES:
            continue
        for needle in CONTENT_NEEDLES:
            line = index.line_of(p, needle)
            if line is None:
                continue
            text = _line_text(index, p, line)
            if needle not in text:
                continue
            add(rel, line, text, needle)

    return out