"""C-PROBER@1 / C-PROBER@6 / C-PROBER@7：计划完整性、零命中仍留轨迹、scanned>=hits、
feature 收窄与判定层同口径。

末尾几条覆盖 C-BASELINE@1 的缺文件回退（任务 T4 要求的最小回归）。
"""

from __future__ import annotations

from pathlib import Path

from gap_engine.baseline import PREVALENCE, PREVALENCE_THRESHOLD, is_prevalent, load_prevalence
from gap_engine.extractors import EXTRACTORS
from gap_engine.index import build_index
from gap_engine.matcher import claim_terms, feature_terms
from gap_engine.prober import (
    ALTERNATE_PLANS,
    CANDIDATE_FILES,
    PLAN,
    ProbeSpec,
    plan,
    run,
    scanned_count,
)
from gap_engine.schema import Claim, ClaimType, Evidence, EvidenceKind, Strength
from gap_engine.spec import claims_from_spec, parse_spec

FIXTURES = Path(__file__).resolve().parents[1] / "contract" / "fixtures"

_NEGATION_PROBE_TYPES = (
    ClaimType.performance,
    ClaimType.concurrency,
    ClaimType.feature,
    ClaimType.testing,
)


def _claim(claim_type: ClaimType = ClaimType.concurrency, text: str = "支持 500 并发用户") -> Claim:
    return Claim(id="c01", text=text, source="readme", type=claim_type)


def test_plan_covers_every_claim_type_with_five_probes() -> None:
    assert set(PLAN) == set(ClaimType)
    for claim_type, specs in PLAN.items():
        expected = 5 if claim_type in _NEGATION_PROBE_TYPES else 4
        assert len(specs) == expected, claim_type
        assert len({spec.probe for spec in specs}) == expected, claim_type
        for spec in specs:
            assert spec.extractor in EXTRACTORS, spec
            assert spec.target


def test_plan_matches_frozen_probe_names() -> None:
    assert [spec.probe for spec in plan(_claim(ClaimType.performance))] == [
        "压测脚本",
        "压测结果",
        "连接池/缓存配置",
        "并发原语",
        "否定/未实现声明",
    ]
    assert [spec.probe for spec in plan(_claim(ClaimType.testing))] == [
        "测试文件",
        "测试配置",
        "覆盖率报告",
        "CI 配置",
        "否定/未实现声明",
    ]
    assert plan(_claim(ClaimType.feature)) == PLAN[ClaimType.feature]


def test_candidate_files_cover_all_extractors() -> None:
    assert set(CANDIDATE_FILES) == set(EXTRACTORS)


def test_run_keeps_trace_when_nothing_hits(tmp_path: Path) -> None:
    index = build_index(tmp_path)
    probes, evidence = run(_claim(), index)
    assert len(probes) == 5
    assert evidence == []
    for probe in probes:
        assert probe.scanned == 0
        assert probe.hits == 0
        assert probe.where == []


def test_run_on_fixture_records_partial_evidence() -> None:
    index = build_index(FIXTURES / "fx-concurrency")
    probes, evidence = run(_claim(), index)
    assert len(probes) == 5
    for probe in probes:
        assert probe.scanned >= probe.hits

    bench_probe = probes[0]
    assert bench_probe.probe == "压测脚本"
    assert bench_probe.hits == 0
    assert bench_probe.where == []
    assert bench_probe.scanned > 0, "无压测脚本时也应说明查过多少处"

    worker_probe = probes[2]
    assert worker_probe.probe == "worker 配置"
    assert worker_probe.hits >= 1
    assert any(loc.startswith("gunicorn.conf.py:") for loc in worker_probe.where)
    assert all(":" in loc for loc in worker_probe.where)

    assert any(item.kind is EvidenceKind.config for item in evidence)
    assert any("gunicorn.conf.py" == item.file for item in evidence)


def test_scanned_count_matches_index_facts() -> None:
    index = build_index(FIXTURES / "fx-concurrency")
    assert scanned_count("structure", index) == len(index.files)
    assert scanned_count("entry", index) == 2
    assert scanned_count("unknown-extractor", index) == len(index.files)


def test_plan_fills_where_contains_per_probe() -> None:
    performance = plan(_claim(ClaimType.performance))
    assert performance[0].where_contains == ("locust", "k6", "wrk", "ab", "jmeter", "benchmark")
    assert performance[2].where_contains == ("pool", "cache", "workers", "max_connections")
    assert performance[3].where_contains == (
        "threaded",
        "async def",
        "ThreadPool",
        "Lock(",
        "Semaphore",
        "gather",
    )

    feature = plan(_claim(ClaimType.feature))
    assert feature[0].where_contains == ("route", "@app.", "@router", "__main__", "main(")
    assert feature[3].where_contains == ("test_", "_test.")

    testing = plan(_claim(ClaimType.testing))
    assert testing[2].where_contains == (
        ".coverage",
        "coverage.xml",
        "coverage.json",
        "coverage.csv",
        "htmlcov",
    )
    assert testing[3].where_contains == (".github", ".gitlab-ci", "Jenkinsfile", ".travis", "azure-pipelines")

    for claim_type in (ClaimType.architecture, ClaimType.scale, ClaimType.security):
        assert all(spec.where_contains == () for spec in plan(_claim(claim_type)))
    assert all(spec.where_contains for spec in plan(_claim(ClaimType.concurrency))[:4])
    assert plan(_claim(ClaimType.concurrency))[-1].where_contains == ()


def test_scanned_ignores_where_contains_filter() -> None:
    index = build_index(FIXTURES / "fx-testing")
    probes, _ = run(_claim(ClaimType.testing, "测试覆盖率 80%"), index)
    for probe in probes:
        assert probe.scanned >= probe.hits
    assert all(probe.scanned > 0 for probe in probes), "scanned 仍是该抽取器关注的文件数"


def test_fx_testing_probes_are_semantically_separated() -> None:
    index = build_index(FIXTURES / "fx-testing")
    probes, _ = run(_claim(ClaimType.testing, "测试覆盖率 80%"), index)
    by_name = {probe.probe: probe for probe in probes}

    assert by_name["覆盖率报告"].hits == 0
    assert by_name["覆盖率报告"].where == []
    assert by_name["CI 配置"].hits == 0

    assert by_name["测试文件"].where
    assert all(loc.startswith("tests/test_calc.py:") for loc in by_name["测试文件"].where)
    assert by_name["测试配置"].where
    assert all(loc.startswith("pyproject.toml:") for loc in by_name["测试配置"].where)


def test_same_claim_probes_no_longer_share_one_where_set() -> None:
    index = build_index(FIXTURES / "fx-testing")
    probes, _ = run(_claim(ClaimType.testing, "测试覆盖率 80%"), index)
    where_sets = {tuple(probe.where) for probe in probes}
    assert len(where_sets) > 1


def test_only_file_existence_probes_are_path_only() -> None:
    path_only = {
        (claim_type, spec.probe)
        for claim_type, specs in PLAN.items()
        for spec in specs
        if spec.path_only
    }
    assert path_only == {
        (ClaimType.feature, "依赖声明"),
        (ClaimType.testing, "测试配置"),
        (ClaimType.testing, "覆盖率报告"),
        (ClaimType.testing, "CI 配置"),
    }


def test_path_only_probes_ignore_file_content(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[tool.coverage.run]\nsource = ["src"]\n# coverage.xml .coverage htmlcov\n',
        encoding="utf-8",
    )
    index = build_index(tmp_path)
    probes, _ = run(_claim(ClaimType.testing, "测试覆盖率 80%"), index)
    by_name = {probe.probe: probe for probe in probes}

    assert by_name["覆盖率报告"].hits == 0
    assert by_name["覆盖率报告"].where == []
    assert by_name["测试配置"].where == ["pyproject.toml:1"]


def test_content_matched_probes_still_use_snippet() -> None:
    index = build_index(FIXTURES / "fx-concurrency")
    probes, _ = run(_claim(), index)
    by_name = {probe.probe: probe for probe in probes}

    assert by_name["并发原语"].hits >= 1
    assert any(loc.startswith("app.py:") for loc in by_name["并发原语"].where)


def test_fx_feature_dependency_probe_matches_requirements_txt() -> None:
    index = build_index(FIXTURES / "fx-feature")
    probes, _ = run(_claim(ClaimType.feature, "支持 Excel 导出"), index)
    by_name = {probe.probe: probe for probe in probes}

    assert by_name["依赖声明"].hits >= 1
    assert by_name["依赖声明"].where
    assert all(loc.startswith("requirements.txt:") for loc in by_name["依赖声明"].where)


def _fx_spec_claims() -> dict[str, Claim]:
    text = (FIXTURES / "fx-spec" / "requirements.md").read_text(encoding="utf-8")
    return {claim.text: claim for claim in claims_from_spec(parse_spec(text), "requirements.md")}


def _lines_of(rel: str) -> list[str]:
    return (FIXTURES / "fx-spec" / rel).read_text(encoding="utf-8").splitlines()


def _assert_where_lines_contain(where: list[str], rel: str, keyword: str) -> None:
    lines = _lines_of(rel)
    assert where
    for loc in where:
        file, _, lineno = loc.rpartition(":")
        assert file == rel, loc
        assert keyword in lines[int(lineno) - 1].lower(), loc


def test_fx_spec_visualization_probe_hits_are_all_zero() -> None:
    index = build_index(FIXTURES / "fx-spec")
    probes, _ = run(_fx_spec_claims()["提供数据可视化"], index)

    assert len(probes) == 5
    assert all(probe.hits == 0 for probe in probes)
    assert all(probe.where == [] for probe in probes)


def test_fx_spec_login_probe_only_hits_login_lines() -> None:
    index = build_index(FIXTURES / "fx-spec")
    probes, _ = run(_fx_spec_claims()["用户登录"], index)
    router = {probe.probe: probe for probe in probes}["路由/入口"]

    assert router.hits >= 1
    _assert_where_lines_contain(router.where, "app.py", "login")


def test_fx_spec_export_probe_only_hits_export_lines() -> None:
    index = build_index(FIXTURES / "fx-spec")
    probes, _ = run(_fx_spec_claims()["支持 Excel 导出"], index)
    router = {probe.probe: probe for probe in probes}["路由/入口"]

    assert router.hits >= 1
    _assert_where_lines_contain(router.where, "app.py", "export")


def test_fx_spec_feature_claims_no_longer_share_where_sets() -> None:
    index = build_index(FIXTURES / "fx-spec")
    claims = _fx_spec_claims()
    visualization = {p.probe: tuple(p.where) for p in run(claims["提供数据可视化"], index)[0]}
    login = {p.probe: tuple(p.where) for p in run(claims["用户登录"], index)[0]}

    assert visualization != login
    assert visualization["路由/入口"] != login["路由/入口"]


def test_feature_claim_without_any_terms_keeps_class_level_hits() -> None:
    index = build_index(FIXTURES / "fx-spec")
    assert feature_terms("OK") == ()
    assert claim_terms("OK") == ()

    probes, _ = run(_claim(ClaimType.feature, "OK"), index)
    router = {probe.probe: probe for probe in probes}["路由/入口"]

    assert router.hits >= 1


def test_feature_narrowing_falls_back_to_claim_terms() -> None:
    index = build_index(FIXTURES / "fx-spec")
    assert feature_terms("支持多语言") == ()
    assert claim_terms("支持多语言") == ("多语言",)

    probes, _ = run(_claim(ClaimType.feature, "支持多语言"), index)

    assert all(probe.hits == 0 for probe in probes), "兜底关键词在 fx-spec 中不存在，不应报出类级命中"


def test_feature_implementation_probe_moves_to_symbols() -> None:
    impl = {spec.probe: spec for spec in PLAN[ClaimType.feature]}["相关实现"]

    assert impl == ProbeSpec("相关实现", "symbols", "按模块划分的实现文件", ())


def test_symbols_candidate_files_cover_every_symbol_suffix() -> None:
    assert CANDIDATE_FILES["symbols"] == (
        "*.py,*.js,*.jsx,*.ts,*.tsx,*.java,*.cs,*.kt,*.kts,*.scala,"
        "*.go,*.rs,*.rb,*.php,*.swift,*.c,*.h,*.cc,*.cpp,*.cxx,*.hpp,*.hh,*.hxx"
    )


def test_fx_spec_feature_implementation_probe_hits_symbol_lines() -> None:
    index = build_index(FIXTURES / "fx-spec")
    claims = _fx_spec_claims()
    impl = {p.probe: p for p in run(claims["支持 Excel 导出"], index)[0]}["相关实现"]

    assert impl.hits >= 1
    lines = (FIXTURES / "fx-spec" / "app.py").read_text(encoding="utf-8").splitlines()
    for loc in impl.where:
        assert loc.startswith("app.py:")
        line = lines[int(loc.rsplit(":", 1)[1]) - 1]
        assert "def " in line or "class " in line, loc


def test_prevalence_falls_back_when_file_missing(tmp_path: Path) -> None:
    table = load_prevalence(tmp_path / "missing.json")
    assert table == PREVALENCE
    assert table is not PREVALENCE
    assert is_prevalent(ClaimType.feature) is True
    assert is_prevalent(ClaimType.performance) is False
    assert PREVALENCE_THRESHOLD == 0.5


def test_prevalence_overrides_valid_keys_only(tmp_path: Path) -> None:
    path = tmp_path / "prevalence.json"
    path.write_text(
        '{"performance": 0.9, "concurrency": 2.0, "testing": "high", "bogus": 0.1}',
        encoding="utf-8",
    )
    table = load_prevalence(path)
    assert len(table) == len(PREVALENCE)
    assert table[ClaimType.performance] == 0.9
    assert table[ClaimType.concurrency] == PREVALENCE[ClaimType.concurrency]
    assert table[ClaimType.testing] == PREVALENCE[ClaimType.testing]
    assert is_prevalent(ClaimType.performance, table) is True

def test_alternate_plans_are_limited_to_ability_and_testing_types() -> None:
    assert set(ALTERNATE_PLANS) == {
        ClaimType.performance,
        ClaimType.concurrency,
        ClaimType.testing,
    }
    for claim_type, specs in ALTERNATE_PLANS.items():
        assert len(specs) == 1, claim_type
        assert specs[0].extractor == "artifact", claim_type

    assert ALTERNATE_PLANS[ClaimType.performance] == (
        ProbeSpec("压测结果文件", "artifact", "结果/产物文件里的测量痕迹"),
    )
    assert ALTERNATE_PLANS[ClaimType.concurrency] == ALTERNATE_PLANS[ClaimType.performance]
    assert ALTERNATE_PLANS[ClaimType.testing] == (
        ProbeSpec("覆盖率产物", "artifact", "coverage.xml 等覆盖率产物文件"),
    )


def test_plan_round_selects_alternate_or_empty() -> None:
    claim = _claim(ClaimType.concurrency)
    assert plan(claim) == PLAN[ClaimType.concurrency]
    assert plan(claim, 1) == PLAN[ClaimType.concurrency]
    assert plan(claim, 0) == PLAN[ClaimType.concurrency]
    assert plan(claim, 2) == ALTERNATE_PLANS[ClaimType.concurrency]
    assert plan(claim, 3) == ()

    feature = _claim(ClaimType.feature)
    assert plan(feature, 1) == PLAN[ClaimType.feature]
    assert plan(feature, 2) == ()


def test_artifact_candidate_files_follow_contract() -> None:
    assert CANDIDATE_FILES["artifact"] == "*.log,*.csv,*.json,*.txt,*.xml,*.html"


def _stub_artifact(index) -> list[Evidence]:
    rel = index.rel(next(iter(index.files)))
    return [
        Evidence(
            id="ev-artifact-001",
            kind=EvidenceKind.bench,
            file=rel,
            line=1,
            snippet="p95 120ms qps 800",
            supports=[ClaimType.performance, ClaimType.concurrency, ClaimType.testing],
            strength=Strength.medium,
        )
    ]


def test_run_round_two_uses_artifact_extractor(tmp_path: Path, monkeypatch) -> None:
    report = tmp_path / "loadtest" / "report.log"
    report.parent.mkdir()
    report.write_text("p95 120ms qps 800\n", encoding="utf-8")
    monkeypatch.setitem(EXTRACTORS, "artifact", _stub_artifact)
    index = build_index(tmp_path)

    probes, evidence = run(_claim(ClaimType.concurrency), index, 2)

    assert [probe.probe for probe in probes] == ["压测结果文件"]
    assert probes[0].scanned > 0
    assert probes[0].hits == 1
    assert [item.id for item in evidence] == ["ev-artifact-001"]


def test_run_round_one_is_unchanged(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setitem(EXTRACTORS, "artifact", _stub_artifact)
    index = build_index(tmp_path)

    probes, evidence = run(_claim(ClaimType.concurrency), index, 1)

    assert [probe.probe for probe in probes] == [
        spec.probe for spec in PLAN[ClaimType.concurrency]
    ]
    assert evidence == []


def test_negation_candidate_files_follow_contract() -> None:
    assert CANDIDATE_FILES["negation"] == (
        "*.py,*.js,*.ts,*.tsx,*.jsx,*.java,*.go,*.rb,*.sh,"
        "*.md,*.txt,*.toml,*.cfg,*.ini,*.yaml,*.yml"
    )


def test_plan_appends_negation_probe_to_judgeable_types() -> None:
    for claim_type in _NEGATION_PROBE_TYPES:
        specs = PLAN[claim_type]
        assert specs[-1] == ProbeSpec("否定/未实现声明", "negation", "显式否定与未实现声明"), claim_type
        assert sum(spec.probe == "否定/未实现声明" for spec in specs) == 1, claim_type

    for claim_type in (ClaimType.architecture, ClaimType.scale, ClaimType.security):
        assert all(spec.extractor != "negation" for spec in PLAN[claim_type]), claim_type


def test_alternate_plans_do_not_probe_negation() -> None:
    for claim_type, specs in ALTERNATE_PLANS.items():
        assert all(spec.probe != "否定/未实现声明" for spec in specs), claim_type


def test_negation_probe_leaves_existing_fixtures_untouched() -> None:
    cases = [
        ("fx-concurrency", _claim(ClaimType.concurrency)),
        ("fx-testing", _claim(ClaimType.testing, "测试覆盖率 80%")),
        ("fx-feature", _claim(ClaimType.feature, "支持 Excel 导出")),
        ("fx-spec", _claim(ClaimType.feature, "支持 Excel 导出")),
    ]
    for fixture, claim in cases:
        index = build_index(FIXTURES / fixture)
        probes, _ = run(claim, index)
        negation = {probe.probe: probe for probe in probes}["否定/未实现声明"]
        assert negation.hits == 0, fixture
        assert negation.where == [], fixture
        assert negation.scanned > 0, fixture

def test_feature_narrowing_reuses_word_boundary(tmp_path: Path) -> None:
    """C-PROBER@8：收窄用 matcher.mentions，短词不得命中标识符内部。"""
    (tmp_path / "logging.py").write_text("def getLevelNamesMapping():\n    pass\n", encoding="utf-8")
    (tmp_path / "runner.py").write_text("class _writeLnDecorator:\n    pass\n", encoding="utf-8")
    index = build_index(tmp_path)

    probes, _ = run(_claim(ClaimType.feature, "支持 .eln 写实现"), index)
    impl = {probe.probe: probe for probe in probes}["相关实现"]

    assert impl.hits == 0
    assert impl.where == []


def test_feature_narrowing_still_hits_real_word(tmp_path: Path) -> None:
    (tmp_path / "impl.py").write_text("def _run(eln, tu):\n    pass\n", encoding="utf-8")
    index = build_index(tmp_path)

    probes, _ = run(_claim(ClaimType.feature, "支持 .eln 写实现"), index)
    impl = {probe.probe: probe for probe in probes}["相关实现"]

    assert impl.hits == 1
    assert impl.where == ["impl.py:1"]