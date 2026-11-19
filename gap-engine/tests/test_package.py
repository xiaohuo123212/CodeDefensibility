"""五目录打包脚本测试（C-PACKAGE@1 / 验收不变量 A7）。

全部在 ``tempfile``/``tmp_path`` 下的临时根目录进行，不在真实仓库根生成 ``dist/``。
"""

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

import pytest

from tools import package

TOP_LEVEL = {"ppt", "project", "video", "codearts_proof", "readme"}


def _touch(path: Path, text: str = "x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _make_root(tmp_path: Path) -> Path:
    root = tmp_path / "root"
    _touch(root / "ppt" / "outline.md")
    _touch(root / "video" / "script.md")
    _touch(root / "codearts_proof" / "session.md")
    _touch(root / "readme" / "README.md")
    _touch(root / "gap-engine" / "src" / "app.py")

    _touch(root / "gap-engine" / ".env")
    _touch(root / "gap-engine" / "cached.pyc")
    _touch(root / "gap-engine" / "cached.pyo")
    _touch(root / "gap-engine" / "__pycache__" / "app.cpython-311.pyc")
    _touch(root / "gap-engine" / ".git" / "config")
    _touch(root / "gap-engine" / "build" / "lib" / "app.py")
    _touch(root / "gap-engine" / "dist" / "old.zip")
    _touch(root / "gap-engine" / ".pytest_cache" / "v" / "cache")
    _touch(root / "gap-engine" / ".mypy_cache" / "3.11" / "cache.json")
    _touch(root / "gap-engine" / "gap_engine.egg-info" / "PKG-INFO")
    _touch(root / "gap-engine" / "node_modules" / "pkg" / "index.js")
    _touch(root / "gap-engine" / ".tmp" / "regen" / "report.md")
    return root


def _names(archive: Path) -> list[str]:
    with zipfile.ZipFile(archive) as zf:
        return zf.namelist()


def test_toplevel_is_exactly_five_dirs(tmp_path: Path) -> None:
    root = _make_root(tmp_path)

    archive = package.build(root, tmp_path / "dist")

    names = _names(archive)
    assert {name.split("/", 1)[0] for name in names} == TOP_LEVEL
    assert "project/src/app.py" in names
    assert "ppt/outline.md" in names
    assert "video/script.md" in names
    assert "codearts_proof/session.md" in names
    assert "readme/README.md" in names


def test_dirty_files_are_excluded(tmp_path: Path) -> None:
    root = _make_root(tmp_path)

    names = _names(package.build(root, tmp_path / "dist"))

    assert not [name for name in names if name.endswith((".pyc", ".pyo"))]
    assert not [name for name in names if "__pycache__" in name]
    assert not [name for name in names if ".git/" in name]
    assert not [name for name in names if ".pytest_cache" in name]
    assert not [name for name in names if ".mypy_cache" in name]
    assert not [name for name in names if ".egg-info" in name]
    assert not [name for name in names if name.startswith("project/build/")]
    assert not [name for name in names if name.startswith("project/dist/")]
    assert not [name for name in names if name.startswith("project/node_modules/")]
    assert not [name for name in names if name.startswith("project/.tmp/")]
    assert not [name for name in names if Path(name).name == ".env"]


def test_main_prints_archive_and_entries(tmp_path: Path, capsys) -> None:
    root = _make_root(tmp_path)
    out = tmp_path / "dist"
    archive = (out / package.DEFAULT_NAME).resolve()

    code = package.main(["--root", str(root), "--out", str(out)])

    captured = capsys.readouterr()
    assert code == 0
    assert f"archive: {archive}" in captured.out
    assert f"entries: {len(_names(archive))}" in captured.out
    assert captured.err == ""


def test_custom_name(tmp_path: Path) -> None:
    root = _make_root(tmp_path)

    archive = package.build(root, tmp_path / "dist", name="demo.zip")

    assert archive.name == "demo.zip"
    assert archive.is_file()


@pytest.mark.parametrize(
    ("missing", "label"),
    [
        ("ppt", "ppt"),
        ("video", "video"),
        ("codearts_proof", "codearts_proof"),
        ("readme", "readme"),
        ("gap-engine", "project"),
    ],
)
def test_missing_dir_returns_two(tmp_path: Path, capsys, missing: str, label: str) -> None:
    root = _make_root(tmp_path)
    shutil.rmtree(root / missing)
    out = tmp_path / "dist"

    code = package.main(["--root", str(root), "--out", str(out)])

    assert code == 2
    assert f"缺少交付目录：{label}" in capsys.readouterr().err
    assert not (out / package.DEFAULT_NAME).exists()