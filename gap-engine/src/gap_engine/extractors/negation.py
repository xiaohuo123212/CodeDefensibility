"""negation 抽取器：显式否定与未实现声明（C-EXTRACTOR@5）。

只判断"这一行是显式否定"，与某条需求是否相关由 Matcher 判定。
已知语义边界：``仅支持`` 是"支持范围受限"，属于比"不支持"更温和的反证，仍按
``strength=high`` 处理，并保留原文 snippet 供人核。

``TODO`` / ``FIXME`` 行必须同时提到实现相关词才算否定，避免无意义 TODO 泛滥。
"""

from __future__ import annotations

from ..index import RepoIndex
from ..schema import ClaimType, Evidence, EvidenceKind, Strength
from . import SOURCE_LIMIT, _clip

NEGATION_MARKERS: tuple[str, ...] = (
    "不支持",
    "暂不支持",
    "尚未支持",
    "未实现",
    "暂未实现",
    "尚未实现",
    "待实现",
    "not supported",
    "unsupported",
    "not implemented",
    "only supports",
    "仅支持",
)

TODO_MARKERS = ("todo", "fixme")
TODO_CONTEXT = ("实现", "implement", "support")
SUFFIXES = frozenset(
    {
        ".py",
        ".js",
        ".ts",
        ".tsx",
        ".jsx",
        ".java",
        ".go",
        ".rb",
        ".sh",
        ".md",
        ".txt",
        ".toml",
        ".cfg",
        ".ini",
        ".yaml",
        ".yml",
    }
)
CAP = 40
SUPPORTS = [ClaimType.performance, ClaimType.concurrency, ClaimType.feature, ClaimType.testing]

# 参数校验型异常：其消息里的否定词描述的是入参不合法，不是功能未实现。
_EXCEPTION_GUARD = (
    "valueerror(",
    "typeerror(",
    "keyerror(",
    "attributeerror(",
    "assertionerror(",
    "indexerror(",
    "oserror(",
    "lookuperror(",
    "overflowerror(",
)


def _inside_string_literal(text: str, index: int) -> bool:
    prefix = text[:index]
    return prefix.count('"') % 2 == 1 or prefix.count("'") % 2 == 1


def _is_negation_line(text: str) -> bool:
    lowered = text.lower()
    guarded = any(token in lowered for token in _EXCEPTION_GUARD)
    for marker in NEGATION_MARKERS:
        index = lowered.find(marker)
        if index < 0:
            continue
        if guarded and _inside_string_literal(lowered, index):
            continue
        return True
    return any(token in lowered for token in TODO_MARKERS) and any(
        word in lowered for word in TODO_CONTEXT
    )


def extract(index: RepoIndex) -> list[Evidence]:
    out: list[Evidence] = []
    seen: set[tuple[str, int | None]] = set()

    for p in index.files:
        if p.suffix.lower() not in SUFFIXES:
            continue
        rel = index.rel(p)
        for raw in index.read(p, limit=SOURCE_LIMIT).splitlines():
            snippet = raw.strip()
            if not snippet or not _is_negation_line(snippet):
                continue
            line = index.line_of(p, snippet)
            key = (rel, line)
            if key in seen:
                continue
            seen.add(key)
            if len(out) >= CAP:
                return out
            out.append(
                Evidence(
                    id=f"ev-negation-{len(out) + 1:03d}",
                    kind=EvidenceKind.code,
                    file=rel,
                    line=line,
                    snippet=_clip(snippet),
                    supports=list(SUPPORTS),
                    strength=Strength.high,
                )
            )

    return out