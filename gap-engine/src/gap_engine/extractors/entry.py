"""entry 抽取器：进程启动入口与路由/处理函数行（C-EXTRACTOR@3）。

C-EXTRACTOR@3 规定路由证据 `kind=entry`，但 `schema.EvidenceKind` 当前没有 entry 值，
且 ``matcher.judge`` 会丢弃未知 kind 的证据（未知 kind 一律不参与判定）。为保证路由行
真正进入证据集并能成为 feature 需求的定位点，这里用 ``EvidenceKind.code`` 承载路由证据，
并以 ``strength=medium``、``supports=[feature]`` 与启动入口证据区分。
"""

from __future__ import annotations

import re

from ..index import RepoIndex
from ..schema import ClaimType, Evidence, EvidenceKind, Strength
from . import CODE_SUFFIXES, SOURCE_LIMIT, _evidence, _line_text

PATTERNS = ("app.run(", "__main__", "uvicorn.run(", "if __name__")
ROUTE_SUFFIXES = frozenset({".py", ".js"})
ROUTE_RE = re.compile(r"^\s*@(?:app|router|bp|blueprint)\.(?:route|get|post|put|patch|delete)\s*\(")
ROUTE_KIND = EvidenceKind.code
SUPPORTS = [ClaimType.feature]


def extract(index: RepoIndex) -> list[Evidence]:
    out: list[Evidence] = []
    seen: set[tuple[str, int]] = set()

    for p in index.files:
        suffix = p.suffix.lower()
        if suffix not in CODE_SUFFIXES:
            continue
        rel = index.rel(p)

        for pattern in PATTERNS:
            line = index.line_of(p, pattern)
            if line is None or (rel, line) in seen:
                continue
            snippet = _line_text(index, p, line)
            if pattern not in snippet:
                continue
            seen.add((rel, line))
            out.append(
                _evidence(
                    "entry",
                    len(out) + 1,
                    EvidenceKind.code,
                    rel,
                    line,
                    snippet,
                    SUPPORTS,
                    Strength.low,
                )
            )

        if suffix not in ROUTE_SUFFIXES:
            continue
        for raw in index.read(p, limit=SOURCE_LIMIT).splitlines():
            if not ROUTE_RE.match(raw):
                continue
            line = index.line_of(p, raw.strip())
            if line is None or (rel, line) in seen:
                continue
            snippet = _line_text(index, p, line)
            if not ROUTE_RE.match(snippet):
                continue
            seen.add((rel, line))
            out.append(
                _evidence(
                    "entry",
                    len(out) + 1,
                    ROUTE_KIND,
                    rel,
                    line,
                    snippet,
                    SUPPORTS,
                    Strength.medium,
                )
            )

    return out