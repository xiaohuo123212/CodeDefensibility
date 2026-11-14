"""concurrency 抽取器：线程/协程原语与 worker 配置。

``workers=<数字>`` 属于进程配置，命中时 kind=config / strength=medium；
其余代码原语命中为 kind=code / strength=high。
"""

from __future__ import annotations

import re

from ..index import RepoIndex
from ..schema import ClaimType, Evidence, EvidenceKind, Strength
from . import CODE_SUFFIXES, CONFIG_SUFFIXES, _evidence, _line_text

SUPPORTS = [ClaimType.concurrency]
CAP = 40
_WORKERS = re.compile(r"workers\s*=\s*\d+")

HITS: tuple[tuple[str, re.Pattern[str] | None, EvidenceKind, Strength], ...] = (
    ("threaded=True", None, EvidenceKind.code, Strength.high),
    ("ThreadPoolExecutor", None, EvidenceKind.code, Strength.high),
    ("async def", None, EvidenceKind.code, Strength.high),
    ("workers", _WORKERS, EvidenceKind.config, Strength.medium),
    ("Lock()", None, EvidenceKind.code, Strength.high),
    ("Semaphore(", None, EvidenceKind.code, Strength.high),
    ("asyncio.gather", None, EvidenceKind.code, Strength.high),
)


def extract(index: RepoIndex) -> list[Evidence]:
    out: list[Evidence] = []
    seen: set[tuple[str, int, str]] = set()

    for p in index.files:
        if p.suffix.lower() not in CODE_SUFFIXES | CONFIG_SUFFIXES:
            continue
        rel = index.rel(p)
        for needle, pattern, kind, strength in HITS:
            line = index.line_of(p, needle)
            if line is None:
                continue
            snippet = _line_text(index, p, line)
            if needle not in snippet:
                continue
            if pattern is not None and not pattern.search(snippet):
                continue
            key = (rel, line, needle)
            if key in seen:
                continue
            seen.add(key)
            if len(out) >= CAP:
                return out
            out.append(
                _evidence(
                    "concurrency",
                    len(out) + 1,
                    kind,
                    rel,
                    line,
                    snippet,
                    SUPPORTS,
                    strength,
                )
            )

    return out