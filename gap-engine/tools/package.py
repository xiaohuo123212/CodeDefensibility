"""五目录交付打包脚本（C-PACKAGE@1）。

默认把仓库根下的 ``ppt/ video/ codearts_proof/ readme/`` 与 ``gap-engine/``（zip 内改名
``project/``）打成一个 zip；只读源目录，不修改任何交付物。
"""

from __future__ import annotations

import argparse
import os
import sys
import zipfile
from pathlib import Path

TOP_DIRS: tuple[tuple[str, str], ...] = (
    ("ppt", "ppt"),
    ("video", "video"),
    ("codearts_proof", "codearts_proof"),
    ("readme", "readme"),
    ("project", "gap-engine"),
)

EXCLUDED_SEGMENTS = frozenset(
    {"__pycache__", ".git", "build", "dist", ".pytest_cache", ".mypy_cache", "node_modules"}
)
EXCLUDED_NAMES = frozenset({".env"})
EXCLUDED_SUFFIXES = frozenset({".pyc", ".pyo"})
EGG_INFO_SUFFIX = ".egg-info"

DEFAULT_NAME = "gap-engine-v1.0.zip"


def _excluded_part(part: str) -> bool:
    return part in EXCLUDED_SEGMENTS or part.endswith(EGG_INFO_SUFFIX)


def _excluded_file(name: str) -> bool:
    return name in EXCLUDED_NAMES or Path(name).suffix.lower() in EXCLUDED_SUFFIXES


def _collect(src: Path, prefix: str) -> list[tuple[Path, str]]:
    entries: list[tuple[Path, str]] = []
    for dirpath, dirnames, filenames in os.walk(src):
        base = Path(dirpath)
        dirnames[:] = sorted(name for name in dirnames if not _excluded_part(name))
        for name in sorted(filenames):
            if _excluded_part(name) or _excluded_file(name):
                continue
            path = base / name
            entries.append((path, f"{prefix}/{path.relative_to(src).as_posix()}"))
    return entries


def build(root: str | Path, out: str | Path, name: str = DEFAULT_NAME) -> Path:
    root = Path(root)
    for label, source in TOP_DIRS:
        if not (root / source).is_dir():
            raise FileNotFoundError(f"缺少交付目录：{label}")

    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    archive = (out / name).resolve()

    entries: list[tuple[Path, str]] = []
    for label, source in TOP_DIRS:
        entries.extend(_collect(root / source, label))

    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        for path, arcname in entries:
            zf.write(path, arcname)

    print(f"archive: {archive}")
    print(f"entries: {len(entries)}")
    return archive


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="package", description="打包五目录交付 zip")
    parser.add_argument("--root", default=None)
    parser.add_argument("--out", default=None)
    parser.add_argument("--name", default=DEFAULT_NAME)
    args = parser.parse_args(argv)

    root = Path(args.root) if args.root else Path(__file__).resolve().parents[2]
    out = Path(args.out) if args.out else root / "dist"

    try:
        build(root, out, args.name)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())