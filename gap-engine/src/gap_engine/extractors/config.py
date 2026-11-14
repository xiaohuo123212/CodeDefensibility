"""config 抽取器：部署/进程/连接池配置痕迹。"""

from __future__ import annotations

import re

from ..index import RepoIndex
from ..schema import ClaimType, Evidence, EvidenceKind, Strength
from . import SCAN_SUFFIXES, _evidence, _line_text

SUPPORTS = [ClaimType.performance, ClaimType.concurrency]
CAP = 40
NAME_HINTS = ("gunicorn.conf.py", "dockerfile", "docker-compose", ".env.example")
CONTENT_HITS: tuple[tuple[str, re.Pattern[str] | None], ...] = (
    ("workers", re.compile(r"workers\s*=\s*\d+")),
    ("pool_size", None),
    ("max_connections", None),
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
                "config",
                len(out) + 1,
                EvidenceKind.config,
                rel,
                line,
                snippet,
                SUPPORTS,
                Strength.medium,
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
        for needle, pattern in CONTENT_HITS:
            line = index.line_of(p, needle)
            if line is None:
                continue
            text = _line_text(index, p, line)
            if needle not in text:
                continue
            if pattern is not None and not pattern.search(text):
                continue
            add(rel, line, text, needle)

    return out