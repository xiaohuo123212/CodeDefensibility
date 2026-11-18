"""C-INDEX@2 回归测试：文件收集、相对路径、懒加载文本、行号来源、扩表与截断标记。"""

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


def test_skips_archived_snapshot_directories(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("print(1)\n", encoding="utf-8")
    for skipped in ("_archive", "_archived", "archive", "_old", "old", "deprecated"):
        target = tmp_path / "pkg" / skipped
        target.mkdir(parents=True)
        (target / "stale.py").write_text("stale = True\n", encoding="utf-8")

    index = build_index(tmp_path)

    assert [index.rel(p) for p in index.files] == ["main.py"]


def test_max_files_bounds_the_index(tmp_path: Path) -> None:
    for i in range(5):
        (tmp_path / f"m{i}.py").write_text(f"v = {i}\n", encoding="utf-8")

    assert len(build_index(tmp_path, max_files=2).files) == 2
    assert build_index(tmp_path, max_files=0).files == ()


def test_truncated_is_false_when_every_file_fits(tmp_path: Path) -> None:
    for i in range(3):
        (tmp_path / f"m{i}.py").write_text(f"v = {i}\n", encoding="utf-8")

    index = build_index(tmp_path, max_files=3)

    assert len(index.files) == 3
    assert index.truncated is False


def test_truncated_is_true_when_max_files_stops_the_walk(tmp_path: Path) -> None:
    for i in range(5):
        (tmp_path / f"m{i}.py").write_text(f"v = {i}\n", encoding="utf-8")

    index = build_index(tmp_path, max_files=2)

    assert [index.rel(p) for p in index.files] == ["m0.py", "m1.py"]
    assert index.truncated is True


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

def test_indexes_c_and_cpp_sources(tmp_path: Path) -> None:
    for name in ("main.c", "app.h", "impl.cc", "impl.cpp", "impl.cxx", "api.hpp", "api.hh", "api.hxx"):
        (tmp_path / name).write_text("int main(void) { return 0; }\n", encoding="utf-8")

    index = build_index(tmp_path)

    assert [index.rel(p) for p in index.files] == [
        "api.hh",
        "api.hpp",
        "api.hxx",
        "app.h",
        "impl.cc",
        "impl.cpp",
        "impl.cxx",
        "main.c",
    ]
    assert len(index.by_suffix(".h", ".hpp")) == 2

def test_skips_generated_build_dirs_by_prefix(tmp_path: Path) -> None:
    for name in ("build-cmake", "cmake-build-debug", "CMakeFiles"):
        target = tmp_path / name
        target.mkdir()
        (target / "cache.txt").write_text("generated\n", encoding="utf-8")
    (tmp_path / "main.cpp").write_text("int main() { return 0; }\n", encoding="utf-8")

    index = build_index(tmp_path)

    assert [index.rel(p) for p in index.files] == ["main.cpp"]


def test_skips_legacy_build_dir_case_insensitively(tmp_path: Path) -> None:
    (tmp_path / "Build").mkdir()
    (tmp_path / "Build" / "out.txt").write_text("generated\n", encoding="utf-8")
    (tmp_path / "keep.py").write_text("x = 1\n", encoding="utf-8")

    index = build_index(tmp_path)

    assert [index.rel(p) for p in index.files] == ["keep.py"]


def test_ignore_file_excludes_paths_and_globs(tmp_path: Path) -> None:
    (tmp_path / ".ignore").write_text(
        "# 归档与生成物\n"
        "\n"
        "editors/vscode/python/archive_specs.py\n"
        "docs/generated/\n"
        "*.min.js\n",
        encoding="utf-8",
    )
    nested = tmp_path / "editors" / "vscode" / "python"
    nested.mkdir(parents=True)
    (nested / "archive_specs.py").write_text("x = 1\n", encoding="utf-8")
    (nested / "runtime.py").write_text("y = 2\n", encoding="utf-8")
    generated = tmp_path / "docs" / "generated"
    generated.mkdir(parents=True)
    (generated / "spec.md").write_text("generated\n", encoding="utf-8")
    (tmp_path / "app.min.js").write_text("var a = 1;\n", encoding="utf-8")
    (tmp_path / "app.js").write_text("var a = 1;\n", encoding="utf-8")

    index = build_index(tmp_path)

    assert [index.rel(p) for p in index.files] == ["app.js", "editors/vscode/python/runtime.py"]


def test_ignore_file_absent_or_comment_only_changes_nothing(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text("x = 1\n", encoding="utf-8")
    baseline = [build_index(tmp_path).rel(p) for p in build_index(tmp_path).files]

    (tmp_path / ".ignore").write_text("# 只有注释\n\n", encoding="utf-8")
    after = [build_index(tmp_path).rel(p) for p in build_index(tmp_path).files]

    assert after == baseline == ["app.py"]


def test_ignore_file_itself_is_not_indexed(tmp_path: Path) -> None:
    (tmp_path / ".ignore").write_text("keep.py\n", encoding="utf-8")
    (tmp_path / "keep.py").write_text("x = 1\n", encoding="utf-8")

    index = build_index(tmp_path)

    assert ".ignore" not in [index.rel(p) for p in index.files]

def test_skips_oss_scanner_output_dir(tmp_path: Path) -> None:
    scanner = tmp_path / ".oss-scanner"
    scanner.mkdir()
    (scanner / "report.md").write_text("scanner output\n", encoding="utf-8")
    (tmp_path / "app.py").write_text("x = 1\n", encoding="utf-8")

    index = build_index(tmp_path)

    assert [index.rel(p) for p in index.files] == ["app.py"]