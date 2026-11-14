"""tests 抽取器：测试文件、pytest 配置与依赖、覆盖率配置。"""

from __future__ import annotations

import re
from pathlib import Path

from ..index import RepoIndex
from ..schema import ClaimType, Evidence, EvidenceKind, Strength
from . import SCAN_SUFFIXES, _evidence, _line_text

SUPPORTS = [ClaimType.testing]
CAP = 40
NAME_PATTERNS = (
    re.compile(r"^test_.*\.py$"),
    re.compile(r"^.*_test\.py$"),
    re.compile(r"^test_.*\.js$"),
)
CONFIG_NEEDLES = ("[tool.pytest", "[tool.coverage")
REQUIREMENT_FILES = (".txt", ".toml", ".cfg", ".ini")


def _is_test_name(name: str) -> bool:
    return any(p.match(name.lower()) for p in NAME_PATTERNS)


def _pytest_dep(index: RepoIndex, p: Path) -> tuple[int, str] | None:
    name = p.name.lower()
    if not (name.startswith("requirements") or name in {"pyproject.toml", "setup.cfg", "tox.ini"}):
        return None
    line = index.line_of(p, "pytest")
    if line is None:
        return None
    snippet = _line_text(index, p, line)
    # 章节标题（[tool.pytest.ini_options]）不是依赖声明
    if "pytest" not in snippet.lower() or snippet.strip().startswith("["):
        return None
    return line, snippet


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
                "tests",
                len(out) + 1,
                EvidenceKind.test,
                rel,
                line,
                snippet,
                SUPPORTS,
                Strength.high,
            )
        )

    for p in index.files:
        if not _is_test_name(p.name):
            continue
        line = index.line_of(p, "test")
        if line is None:
            continue
        snippet = _line_text(index, p, line)
        if "test" in snippet.lower():
            add(index.rel(p), line, snippet, "file")

    for p in index.files:
        suffix = p.suffix.lower()
        if suffix not in SCAN_SUFFIXES and suffix not in REQUIREMENT_FILES:
            continue
        for needle in CONFIG_NEEDLES:
            line = index.line_of(p, needle)
            if line is None:
                continue
            snippet = _line_text(index, p, line)
            if needle in snippet:
                add(index.rel(p), line, snippet, needle)

        dep = _pytest_dep(index, p)
        if dep is not None:
            add(index.rel(p), dep[0], dep[1], "dep")

        rel = index.rel(p)
        if rel == ".coveragerc" or rel.endswith("/.coveragerc"):
            line = index.line_of(p, "coverage")
            if line is not None:
                snippet = _line_text(index, p, line)
                if snippet:
                    add(rel, line, snippet, "coveragerc")

    return out