"""C-INDEX@1 回归测试：文件收集、相对路径、懒加载文本、行号来源。"""

from __future__ import annotations

from pathlib import Path

import pytest

from gap_engine.index import MAX_FILE_BYTES, build_index

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "contract" / "fixtures"


def _fixture(name: str) -> Path:
    return FIXTURES / name


def test_build_index_collects_sorted_posix_relative_paths() -> None:
    index = build_index(_fixture("fx-testing"))
    names = [index.rel(p) for p in index.files]

    assert names, "fx-testing 应至少索引到一个文件"
    assert "README.md" in names
    assert "src/calc.py" in names
    assert "tests/test_calc.py" in names
    assert names == sorted(names)
    assert all("\\" not in name for name in names)
    assert all(Path(name).is_absolute() is False for name in names)


def test_rel_read_and_text_are_lazy_and_truncated() -> None:
    index = build_index(_fixture("fx-feature"))
    app = next(p for p in index.files if p.name == "app.py")
    full = app.read_text(encoding="utf-8")

    assert index.rel(app) == "app.py"
    assert index.read(app) == full[:4000]
    assert index.read(app, limit=10) == full[:10]
    assert index.read(_fixture("fx-feature") / "missing.py") == ""
    assert index.text()["app.py"] == full[:4000]
    assert index.text() is index.text(), "text() 应缓存同一份字典"


def test_by_suffix_filters_and_accepts_with_or_without_dot() -> None:
    index = build_index(_fixture("fx-feature"))
    expected = [p for p in index.files if p.suffix == ".py"]

    assert index.by_suffix(".py") == expected
    assert index.by_suffix("py") == expected
    assert index.by_suffix(".py", ".txt") != expected


def test_line_of_is_one_based_and_returns_none_when_missing() -> None:
    index = build_index(_fixture("fx-feature"))
    app = next(p for p in index.files if p.name == "app.py")
    expected = app.read_text(encoding="utf-8").splitlines().index('@app.get("/export")') + 1

    assert index.line_of(app, '@app.get("/export")') == expected
    assert index.line_of(app, "definitely-not-there") is None


def test_skips_noise_dirs_binaries_and_oversized_files(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text("print(1)\n", encoding="utf-8")
    (tmp_path / "image.png").write_bytes(b"binary")
    (tmp_path / "big.py").write_text("x" * MAX_FILE_BYTES, encoding="utf-8")
    for skipped in (".git", "node_modules", "__pycache__", ".venv", "dist", "build", "htmlcov"):
        target = tmp_path / skipped
        target.mkdir()
        (target / "noise.py").write_text("noise = True\n", encoding="utf-8")

    index = build_index(tmp_path)

    assert [index.rel(p) for p in index.files] == ["app.py"]


def test_max_files_bounds_the_index(tmp_path: Path) -> None:
    for i in range(5):
        (tmp_path / f"m{i}.py").write_text(f"v = {i}\n", encoding="utf-8")

    assert len(build_index(tmp_path, max_files=2).files) == 2
    assert build_index(tmp_path, max_files=0).files == ()


def test_missing_root_raises_file_not_found(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        build_index(tmp_path / "nope")


def test_empty_repo_index_is_empty_and_does_not_raise(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()

    index = build_index(empty)

    assert index.files == ()
    assert index.text() == {}
    assert index.by_suffix(".py") == []


def test_indexes_result_and_artifact_suffixes(tmp_path: Path) -> None:
    for name in ("bench.log", "result.csv", "coverage.xml", "index.html"):
        (tmp_path / name).write_text("p95 latency = 120ms\n", encoding="utf-8")

    index = build_index(tmp_path)

    assert [index.rel(p) for p in index.files] == [
        "bench.log",
        "coverage.xml",
        "index.html",
        "result.csv",
    ]


def test_htmlcov_directory_is_still_skipped(tmp_path: Path) -> None:
    (tmp_path / "coverage.xml").write_text("<coverage/>\n", encoding="utf-8")
    htmlcov = tmp_path / "htmlcov"
    htmlcov.mkdir()
    (htmlcov / "index.html").write_text("<html>coverage</html>\n", encoding="utf-8")

    index = build_index(tmp_path)

    assert [index.rel(p) for p in index.files] == ["coverage.xml"]