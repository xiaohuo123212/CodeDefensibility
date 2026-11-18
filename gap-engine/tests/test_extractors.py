"""C-EXTRACTOR@1/@2/@3/@4/@5/@6 回归测试：注册、证据下限、行号、路由证据、产物证据、否定证据、符号行、空仓行为。"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

from gap_engine.extractors import EXTRACTORS
from gap_engine.extractors.negation import NEGATION_MARKERS
from gap_engine.index import RepoIndex, build_index
from gap_engine.schema import ClaimType, Evidence, EvidenceKind, Strength

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "contract" / "fixtures"
EXTRACTOR_NAMES = (
    "structure",
    "deps",
    "entry",
    "concurrency",
    "tests",
    "bench",
    "config",
    "artifact",
    "negation",
    "symbols",
)
NON_STATISTICAL = (
    "deps",
    "entry",
    "concurrency",
    "tests",
    "bench",
    "config",
    "artifact",
    "negation",
    "symbols",
)
FIXTURE_NAMES = ("fx-concurrency", "fx-feature", "fx-testing")


def _extract(name: str, fixture: str) -> list[Evidence]:
    return EXTRACTORS[name](build_index(FIXTURES / fixture))


def _assert_well_formed(name: str, items: list[Evidence]) -> None:
    for seq, item in enumerate(items, start=1):
        assert isinstance(item, Evidence)
        assert item.id == f"ev-{name}-{seq:03d}"
        assert not Path(item.file).is_absolute(), item.file
        assert "\\" not in item.file, item.file
        assert item.line >= 1
        assert item.snippet
        assert "\n" not in item.snippet and len(item.snippet) <= 120


def _flatten(line: str) -> str:
    return " ".join(line.split())[:120]


def test_registry_exposes_the_nine_extractors() -> None:
    assert set(EXTRACTORS) == set(EXTRACTOR_NAMES)
    for name in EXTRACTOR_NAMES:
        module = importlib.import_module(f"gap_engine.extractors.{name}")
        assert callable(module.extract)
        assert EXTRACTORS[name] is module.extract


@pytest.mark.parametrize("fixture", FIXTURE_NAMES)
def test_all_extractors_emit_well_formed_evidence(fixture: str) -> None:
    for name in EXTRACTOR_NAMES:
        items = _extract(name, fixture)
        _assert_well_formed(name, items)


def test_structure_reports_file_count_total_lines_and_largest_file() -> None:
    index = build_index(FIXTURES / "fx-feature")
    items = EXTRACTORS["structure"](index)

    assert len(items) == 3
    assert all(item.kind is EvidenceKind.code for item in items)
    assert all(item.strength is Strength.low for item in items)
    assert all(item.line == 1 for item in items)
    assert all(item.file in {index.rel(p) for p in index.files} for item in items)
    assert items[0].snippet.startswith("files=")
    assert items[1].snippet.startswith("loc=")
    assert str(len(index.files)) in items[0].snippet


def test_deps_finds_requirements_for_feature_and_concurrency_fixtures() -> None:
    feature = _extract("deps", "fx-feature")
    concurrency = _extract("deps", "fx-concurrency")

    assert len(feature) >= 2
    assert "openpyxl" in " ".join(item.snippet for item in feature)
    assert "gunicorn" in " ".join(item.snippet for item in concurrency)
    assert all(item.kind is EvidenceKind.dep for item in feature + concurrency)
    assert all(item.strength is Strength.medium for item in feature + concurrency)
    assert all(ClaimType.feature in item.supports for item in feature)
    assert all(item.file == "requirements.txt" for item in feature)
    assert len({item.snippet for item in feature}) == len(feature), "依赖名应去重"


def test_deps_line_points_at_the_declaration_not_the_file_head() -> None:
    items = _extract("deps", "fx-feature")
    openpyxl = next(item for item in items if "openpyxl" in item.snippet)

    assert openpyxl.line == 2
    assert openpyxl.snippet == "openpyxl"


def test_deps_is_empty_without_dependency_manifests() -> None:
    assert _extract("deps", "fx-testing") == []


def test_deps_joins_backslash_continuations(tmp_path: Path) -> None:
    (tmp_path / "requirements.txt").write_text(
        "openpyxl>=3.0 \\\n"
        "    --hash=sha256:abc\n"
        "gunicorn\n",
        encoding="utf-8",
    )

    items = EXTRACTORS["deps"](build_index(tmp_path))

    assert [item.snippet for item in items] == ["openpyxl>=3.0 \\", "gunicorn"]
    assert [item.line for item in items] == [1, 3]


def test_entry_finds_main_guarded_startup() -> None:
    for fixture in ("fx-concurrency", "fx-feature"):
        items = _extract("entry", fixture)
        startup = [
            item
            for item in items
            if "__main__" in item.snippet or "app.run(" in item.snippet
        ]
        assert startup, fixture
        assert all(item.kind is EvidenceKind.code for item in startup)
        assert all(item.strength is Strength.low for item in startup)

    assert _extract("entry", "fx-testing") == []



@pytest.mark.parametrize("fixture", ("fx-feature", "fx-spec"))
def test_entry_route_line_is_feature_evidence(fixture: str) -> None:
    index = build_index(FIXTURES / fixture)
    items = EXTRACTORS["entry"](index)
    routes = [
        item for item in items if Path(item.file).name == "app.py" and "/export" in item.snippet
    ]

    assert routes, f"{fixture} 的 /export 路由行应成为 entry 证据"
    assert all(item.kind is EvidenceKind.code for item in routes)
    assert all(item.strength is Strength.medium for item in routes)
    assert all(ClaimType.feature in item.supports for item in routes)

    expected = (
        (index.root / routes[0].file)
        .read_text(encoding="utf-8")
        .splitlines()
        .index(routes[0].snippet.strip())
        + 1
    )
    assert routes[0].line == expected


def test_entry_route_evidence_is_deduplicated_per_line() -> None:
    index = build_index(FIXTURES / "fx-spec")
    items = EXTRACTORS["entry"](index)
    keys = [(item.file, item.line) for item in items]

    assert len(keys) == len(set(keys))
    assert [item.snippet for item in items].count('@app.route("/export")') == 1


def test_concurrency_separates_code_primitives_from_worker_config() -> None:
    items = _extract("concurrency", "fx-concurrency")
    assert len(items) >= 2

    workers = [item for item in items if "workers" in item.snippet]
    code_hits = [item for item in items if "workers" not in item.snippet]

    assert workers, "gunicorn.conf.py 的 workers 应被抽到"
    assert all(item.kind is EvidenceKind.config for item in workers)
    assert all(item.strength is Strength.medium for item in workers)
    assert all(item.file == "gunicorn.conf.py" and item.line == 2 for item in workers)
    assert code_hits
    assert all(item.kind is EvidenceKind.code for item in code_hits)
    assert all(item.strength is Strength.high for item in code_hits)
    assert all(ClaimType.concurrency in item.supports for item in items)


def test_tests_finds_test_file_pytest_and_coverage_config() -> None:
    items = _extract("tests", "fx-testing")
    located = " ".join(f"{item.file} {item.snippet}" for item in items)

    assert len(items) >= 3
    assert "tests/test_calc.py" in located
    assert "[tool.pytest" in located
    assert "[tool.coverage" in located
    assert all(item.kind is EvidenceKind.test for item in items)
    assert all(item.strength is Strength.high for item in items)
    assert all(ClaimType.testing in item.supports for item in items)


@pytest.mark.parametrize("fixture", FIXTURE_NAMES)
def test_bench_is_absent_in_all_fixtures(fixture: str) -> None:
    assert _extract("bench", fixture) == [], f"{fixture} 不应存在压测证据"


def test_bench_detects_locust_script_and_virtual_users(tmp_path: Path) -> None:
    (tmp_path / "locustfile.py").write_text(
        "from locust import HttpUser\n\nclass U(HttpUser):\n    users = 500\n",
        encoding="utf-8",
    )
    items = EXTRACTORS["bench"](build_index(tmp_path))

    assert items
    assert all(item.kind is EvidenceKind.bench for item in items)
    assert all(item.strength is Strength.high for item in items)
    assert set(items[0].supports) == {ClaimType.performance, ClaimType.concurrency}
    assert {item.file for item in items} == {"locustfile.py"}
    assert min(item.line for item in items) == 1
    assert all("locust" in item.snippet for item in items)


def test_config_reports_gunicorn_workers_on_the_real_line() -> None:
    items = _extract("config", "fx-concurrency")
    files = {item.file for item in items}

    assert items
    assert "gunicorn.conf.py" in files
    workers = [item for item in items if "workers" in item.snippet]
    assert workers
    assert all(item.line == 2 for item in workers)
    assert all(item.snippet == "workers = 4" for item in workers)
    assert all(item.kind is EvidenceKind.config for item in items)
    assert all(item.strength is Strength.medium for item in items)
    assert all(item.supports == [ClaimType.performance, ClaimType.concurrency] for item in items)


def test_artifact_extracts_measurement_lines_from_result_files(tmp_path: Path) -> None:
    (tmp_path / "bench.log").write_text(
        "warmup done\nP95 latency = 120ms\nall good\n", encoding="utf-8"
    )
    (tmp_path / "result.csv").write_text("metric,value\np95_latency_ms,120\n", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("nothing measured here\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("P95 latency = 120ms，支持 500 并发\n", encoding="utf-8")

    items = EXTRACTORS["artifact"](build_index(tmp_path))

    assert [item.file for item in items] == ["bench.log", "result.csv"]
    assert [item.line for item in items] == [2, 2]
    assert [item.id for item in items] == ["ev-artifact-001", "ev-artifact-002"]
    first = items[0]
    assert first.snippet == "P95 latency = 120ms"
    assert first.kind is EvidenceKind.bench
    assert first.strength is Strength.medium
    assert first.supports == [ClaimType.performance, ClaimType.concurrency, ClaimType.testing]


def test_artifact_requires_both_measure_word_and_digit(tmp_path: Path) -> None:
    (tmp_path / "bench.json").write_text('{"latency": "fast"}\n{"qps": 42}\n', encoding="utf-8")

    items = EXTRACTORS["artifact"](build_index(tmp_path))

    assert [item.line for item in items] == [2]
    assert items[0].snippet == '{"qps": 42}'


def test_artifact_accepts_files_whose_name_hints_at_results(tmp_path: Path) -> None:
    (tmp_path / "perf.conf").write_text("throughput = 1200 rps\n", encoding="utf-8")
    (tmp_path / "app.conf").write_text("throughput = 1200 rps\n", encoding="utf-8")

    items = EXTRACTORS["artifact"](build_index(tmp_path))

    assert [item.file for item in items] == ["perf.conf"]


def test_artifact_caps_at_forty_and_dedupes_per_line(tmp_path: Path) -> None:
    lines = [f"qps bench {i} = {1000 + i}" for i in range(45)]
    (tmp_path / "result.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    items = EXTRACTORS["artifact"](build_index(tmp_path))

    assert len(items) == 40
    keys = [(item.file, item.line) for item in items]
    assert len(keys) == len(set(keys))
    assert items[0].id == "ev-artifact-001"
    assert items[-1].id == "ev-artifact-040"


@pytest.mark.parametrize("fixture", FIXTURE_NAMES)
def test_artifact_is_absent_in_fixtures_without_result_files(fixture: str) -> None:
    assert _extract("artifact", fixture) == []


def test_negation_markers_are_literal_and_complete() -> None:
    assert NEGATION_MARKERS == (
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


def test_negation_extracts_negation_and_todo_lines(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text(
        "def export():\n"
        "    # 暂不支持批量导出\n"
        "    return 1\n"
        "\n"
        "# TODO: 实现分页\n"
        "# TODO: rename helper\n",
        encoding="utf-8",
    )
    (tmp_path / "README.md").write_text(
        "Not supported yet.\nOnly supports CSV.\n", encoding="utf-8"
    )

    items = EXTRACTORS["negation"](build_index(tmp_path))

    assert {(item.file, item.line) for item in items} == {
        ("app.py", 2),
        ("app.py", 5),
        ("README.md", 1),
        ("README.md", 2),
    }
    assert len(items) == 4
    assert all(item.kind is EvidenceKind.code for item in items)
    assert all(item.strength is Strength.high for item in items)
    assert all(
        item.supports
        == [ClaimType.performance, ClaimType.concurrency, ClaimType.feature, ClaimType.testing]
        for item in items
    )
    assert [item.id for item in items] == [f"ev-negation-{n:03d}" for n in range(1, 5)]
    assert all(item.snippet for item in items)
    assert not any("rename helper" in item.snippet for item in items)


def test_negation_ignores_todo_without_implementation_context(tmp_path: Path) -> None:
    (tmp_path / "notes.txt").write_text("TODO: rename helper\nFIXME: formatting\n", encoding="utf-8")

    assert EXTRACTORS["negation"](build_index(tmp_path)) == []


def test_negation_skips_artifact_only_suffixes(tmp_path: Path) -> None:
    (tmp_path / "bench.log").write_text("not supported in csv mode\n", encoding="utf-8")
    (tmp_path / "result.csv").write_text("unsupported,1\n", encoding="utf-8")
    (tmp_path / "data.json").write_text('{"note": "not implemented"}\n', encoding="utf-8")

    assert EXTRACTORS["negation"](build_index(tmp_path)) == []


def test_negation_caps_at_forty_and_dedupes_per_line(tmp_path: Path) -> None:
    lines = [f"功能 {i} 未实现" for i in range(45)]
    (tmp_path / "notes.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    items = EXTRACTORS["negation"](build_index(tmp_path))

    assert len(items) == 40
    assert items[0].id == "ev-negation-001"
    assert items[-1].id == "ev-negation-040"
    assert len({(item.file, item.line) for item in items}) == 40


def test_negation_keeps_evidence_when_line_of_returns_none(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "app.py").write_text("尚未支持导出\n", encoding="utf-8")
    index = build_index(tmp_path)
    monkeypatch.setattr(RepoIndex, "line_of", lambda self, p, needle: None)

    items = EXTRACTORS["negation"](index)

    assert len(items) == 1
    assert items[0].line is None
    assert items[0].snippet == "尚未支持导出"


@pytest.mark.parametrize("fixture", FIXTURE_NAMES)
def test_negation_is_absent_in_fixtures(fixture: str) -> None:
    assert _extract("negation", fixture) == []


def test_negation_skips_negation_words_inside_validation_error_messages(
    tmp_path: Path,
) -> None:
    (tmp_path / "app.py").write_text(
        "def load(fmt):\n"
        '    raise ValueError(f"Unsupported format: {fmt}")\n'
        "    raise KeyError('unsupported key')\n"
        "\n"
        "def other():\n"
        '    raise NotImplementedError("not supported yet")\n',
        encoding="utf-8",
    )

    items = EXTRACTORS["negation"](build_index(tmp_path))

    assert [(item.file, item.line) for item in items] == [("app.py", 6)]
    assert items[0].snippet == 'raise NotImplementedError("not supported yet")'


def test_negation_keeps_marker_outside_the_exception_message(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text(
        'raise ValueError("bad input")  # 暂不支持批量导出\n', encoding="utf-8"
    )

    items = EXTRACTORS["negation"](build_index(tmp_path))

    assert len(items) == 1
    assert items[0].line == 1



def test_symbols_emits_one_first_symbol_line_per_file(tmp_path: Path) -> None:
    (tmp_path / "mod.py").write_text("import os\n\n\ndef export():\n    pass\n", encoding="utf-8")
    (tmp_path / "notes.md").write_text("def looks_like_code():\n", encoding="utf-8")
    (tmp_path / "plain.py").write_text("import os\n", encoding="utf-8")

    items = EXTRACTORS["symbols"](build_index(tmp_path))

    assert [(item.file, item.line) for item in items] == [("mod.py", 4)]
    first = items[0]
    assert first.id == "ev-symbols-001"
    assert first.snippet == "def export():"
    assert first.kind is EvidenceKind.code
    assert first.strength is Strength.low
    assert first.supports == [ClaimType.feature]


def test_symbols_covers_mainstream_languages(tmp_path: Path) -> None:
    cases = {
        "a.py": "class A:",
        "b.js": "export const b = 1;",
        "c.ts": "function c() {}",
        "d.java": "public class D {}",
        "e.go": "func e() {}",
        "f.rs": "fn f() {}",
        "g.cpp": "namespace g {",
        "h.rb": "module H",
        "i.cs": "public enum I {}",
        "j.kt": "interface J",
        "k.scala": "class K",
    }
    for name, line in cases.items():
        (tmp_path / name).write_text(f"// header\n{line}\n", encoding="utf-8")

    items = EXTRACTORS["symbols"](build_index(tmp_path))

    assert {item.file: item.snippet for item in items} == cases
    assert all(item.line == 2 for item in items)


def test_symbols_keeps_at_most_one_evidence_per_file(tmp_path: Path) -> None:
    body = "\n".join(f"def f{i}(): pass" for i in range(50))
    (tmp_path / "many.py").write_text(body + "\n", encoding="utf-8")

    items = EXTRACTORS["symbols"](build_index(tmp_path))

    assert len(items) == 1
    assert items[0].line == 1


@pytest.mark.parametrize("fixture", FIXTURE_NAMES)
def test_evidence_lines_come_from_index_line_of(fixture: str) -> None:
    index = build_index(FIXTURES / fixture)
    for name in NON_STATISTICAL:
        for item in EXTRACTORS[name](index):
            if item.line is None:
                continue
            lines = (index.root / item.file).read_text(encoding="utf-8").splitlines()
            assert _flatten(lines[item.line - 1]) == item.snippet, f"{name}: {item}"


@pytest.mark.parametrize("fixture", FIXTURE_NAMES)
def test_no_extractor_pads_hits_to_line_one(fixture: str) -> None:
    index = build_index(FIXTURES / fixture)
    items = [item for name in NON_STATISTICAL for item in EXTRACTORS[name](index)]

    assert items
    assert any(item.line > 1 for item in items), "命中行不应全部落在第 1 行占位"
    assert not any(
        item.snippet.startswith(("dependency: ", "test file: ", "config file: ", "bench artifact: "))
        for item in items
    ), "snippet 必须是命中行原文，不得是自造描述"


@pytest.mark.parametrize("name", EXTRACTOR_NAMES)
def test_empty_repo_returns_empty_list(name: str, tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()

    assert EXTRACTORS[name](build_index(empty)) == []