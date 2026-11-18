"""仓库索引（C-INDEX@2）：一次遍历产出全部抽取器共用的只读证据视图。

索引只读取文本文件，从不执行、导入或安装被分析仓库。
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

SKIP_DIRS = frozenset(
    {
        ".git",
        "node_modules",
        "__pycache__",
        ".venv",
        "dist",
        "build",
        "htmlcov",
        "_archive",
        "_archived",
        "archive",
        "_old",
        "old",
        "deprecated",
        "cmakefiles",
        ".oss-scanner",
    }
)

# 生成目录按前缀整棵剪掉：build-cmake/、cmake-build-debug/ 这类不在 SKIP_DIRS 的全等名单里。
SKIP_DIR_PREFIXES = ("build-", "cmake-build-")
IGNORE_FILE = ".ignore"

TEXT_SUFFIXES = frozenset(
    {
        ".py",
        ".js",
        ".ts",
        ".tsx",
        ".jsx",
        ".json",
        ".toml",
        ".cfg",
        ".ini",
        ".yaml",
        ".yml",
        ".md",
        ".txt",
        ".conf",
        ".sh",
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
        ".log",
        ".csv",
        ".xml",
        ".html",
        ".c",
        ".h",
        ".cc",
        ".cpp",
        ".cxx",
        ".hpp",
        ".hh",
        ".hxx",
    }
)

MAX_FILE_BYTES = 400 * 1024
TEXT_LIMIT = 4000


@dataclass(frozen=True)
class RepoIndex:
    root: Path
    files: tuple[Path, ...]
    truncated: bool = False

    def rel(self, p: Path) -> str:
        path = Path(p)
        try:
            return path.resolve().relative_to(self.root).as_posix()
        except ValueError:
            return path.name

    def _raw_text(self, p: Path) -> str:
        try:
            return Path(p).read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""

    def read(self, p: Path, limit: int = TEXT_LIMIT) -> str:
        return self._raw_text(p)[:limit]

    @cached_property
    def _texts(self) -> dict[str, str]:
        return {self.rel(p): self.read(p) for p in self.files}

    def text(self) -> dict[str, str]:
        return self._texts

    def by_suffix(self, *suffixes: str) -> list[Path]:
        wanted = {s.lower() if s.startswith(".") else f".{s.lower()}" for s in suffixes}
        return [p for p in self.files if p.suffix.lower() in wanted]

    def line_of(self, p: Path, needle: str) -> int | None:
        for lineno, line in enumerate(self._raw_text(p).splitlines(), start=1):
            if needle in line:
                return lineno
        return None


def _load_ignore(root: Path) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """读取仓库根 ``.ignore``，返回（路径前缀项, glob 项）；缺失或不可读时两者皆空。"""
    try:
        text = (root / IGNORE_FILE).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return (), ()
    prefixes: list[str] = []
    globs: list[str] = []
    for raw in text.splitlines():
        item = raw.strip().lower().rstrip("/")
        if not item or item.startswith("#"):
            continue
        (globs if "*" in item else prefixes).append(item)
    return tuple(prefixes), tuple(globs)


def _is_ignored(rel: str, prefixes: tuple[str, ...], globs: tuple[str, ...]) -> bool:
    low = rel.lower()
    for item in prefixes:
        if low == item or low.startswith(f"{item}/"):
            return True
    return any(fnmatch.fnmatch(low, pattern) for pattern in globs)


def build_index(root: Path, max_files: int = 4000) -> RepoIndex:
    root_path = Path(root).resolve()
    if not root_path.is_dir():
        raise FileNotFoundError(f"repository not found: {root}")

    ignore_prefixes, ignore_globs = _load_ignore(root_path)
    found: list[Path] = []
    pending: list[Path] = [root_path]
    while pending and len(found) < max_files:
        current = pending.pop(0)
        try:
            entries = sorted(current.iterdir(), key=lambda p: p.name)
        except OSError:
            continue
        for entry in entries:
            if entry.is_symlink():
                continue
            rel = entry.relative_to(root_path).as_posix()
            if _is_ignored(rel, ignore_prefixes, ignore_globs):
                continue
            if entry.is_dir():
                name = entry.name.lower()
                if name in SKIP_DIRS or name.startswith(SKIP_DIR_PREFIXES):
                    continue
                pending.append(entry)
                continue
            if not entry.is_file() or entry.suffix.lower() not in TEXT_SUFFIXES:
                continue
            try:
                if entry.stat().st_size >= MAX_FILE_BYTES:
                    continue
            except OSError:
                continue
            found.append(entry)

    found.sort(key=lambda p: p.relative_to(root_path).as_posix())
    # 单目录一次遍历可能超出 max_files 而不留下 pending，故两种截断都要显式判定。
    truncated = bool(pending) or len(found) > max_files
    return RepoIndex(root=root_path, files=tuple(found[:max_files]), truncated=truncated)
