"""七个确定性规则抽取器（C-EXTRACTOR@1）。

抽取器只读索引、只产出 ``Evidence``：不判 status、不调 LLM、不执行被分析代码。
共享的构造工具集中在本模块，各子模块通过 ``from . import _evidence`` 复用，
因此子模块的导入放在文件末尾，保证工具先完成定义。
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from ..index import RepoIndex
from ..schema import ClaimType, Evidence, EvidenceKind, Strength

SNIPPET_LIMIT = 120
CODE_SUFFIXES = frozenset(
    {
        ".py",
        ".js",
        ".ts",
        ".tsx",
        ".jsx",
        ".java",
        ".cs",
        ".kt",
        ".kts",
        ".scala",
        ".go",
        ".rs",
        ".rb",
        ".php",
        ".swift",
    }
)
CONFIG_SUFFIXES = frozenset({".conf", ".cfg", ".ini", ".toml", ".yaml", ".yml", ".json", ".sh"})
SCAN_SUFFIXES = CODE_SUFFIXES | CONFIG_SUFFIXES
SOURCE_LIMIT = 1_000_000


def _clip(text: str) -> str:
    return " ".join(text.split())[:SNIPPET_LIMIT]


def _evidence(
    name: str,
    seq: int,
    kind: EvidenceKind,
    file: str,
    line: int,
    snippet: str,
    supports: list[ClaimType],
    strength: Strength,
) -> Evidence:
    return Evidence(
        id=f"ev-{name}-{seq:03d}",
        kind=kind,
        file=file,
        line=max(1, int(line)),
        snippet=_clip(snippet),
        supports=list(supports),
        strength=strength,
    )


def _line_text(index: RepoIndex, p: Path, line: int, fallback: str = "") -> str:
    lines = index.read(p, limit=SOURCE_LIMIT).splitlines()
    if 1 <= line <= len(lines):
        return lines[line - 1]
    return fallback


from . import (  # noqa: E402
    artifact,
    bench,
    concurrency,
    config,
    deps,
    entry,
    negation,
    structure,
    symbols,
    tests,
)

EXTRACTORS: dict[str, Callable[[RepoIndex], list[Evidence]]] = {
    "structure": structure.extract,
    "deps": deps.extract,
    "entry": entry.extract,
    "concurrency": concurrency.extract,
    "tests": tests.extract,
    "bench": bench.extract,
    "config": config.extract,
    "artifact": artifact.extract,
    "negation": negation.extract,
    "symbols": symbols.extract,
}

__all__ = ["EXTRACTORS"]