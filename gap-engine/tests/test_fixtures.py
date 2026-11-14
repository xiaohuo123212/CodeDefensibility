"""C-FIXTURE@2/@3 回归测试：README 只留真实声称，事实断言由 EXPECTED.md 承载。"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from gap_engine import cli, prober
from gap_engine.index import build_index
from gap_engine.pipeline import analyze_repo, analyze_spec, render_spec_to, render_to
from gap_engine.schema import ClaimType, Status
from gap_engine.spec import CONCURRENCY_CRITERIA, parse_spec

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "contract" / "fixtures"
FX_SPEC = FIXTURES / "fx-spec"
SPEC_NAME = "requirements.md"
SPEC_TEXTS = ("支持 Excel 导出", "支持 500 并发用户", "用户登录", "高性能", "提供数据可视化")
METRIC_KEYS = {
    "audit_effort_classes",
    "audit_effort_mean_classes",
    "audit_effort_mean_scanned",
    "audit_effort_scanned",
    "coverage_none_rate",
    "locator_rate",
    "n_claims",
    "n_contradicted",
    "n_judgeable",
    "n_no_evidence",
    "n_supported",
    "no_evidence_rate",
}
BENCH_NAME_HINTS = ("locust", "k6", "benchmark", "ab_test")
META_WORDS = ("用途", "被断言", "应被判", "回归基线", "no_evidence", "supported", "contradicted")
CLAIMS = {
    "fx-concurrency": "支持 500 并发用户",
    "fx-feature": "支持 Excel 导出",
    "fx-testing": "测试覆盖率 80%",
}


def _read(*parts: str) -> str:
    return FIXTURES.joinpath(*parts).read_text(encoding="utf-8")


def _file_names(fixture: str) -> str:
    return " ".join(p.name.lower() for p in (FIXTURES / fixture).rglob("*") if p.is_file())


def _verdict_for(fixture: str, needle: str):
    claims, verdicts = analyze_repo(FIXTURES / fixture)
    by_id = {claim.id: claim for claim in claims}
    pairs = [(by_id[v.claim_id], v) for v in verdicts if v.claim_id in by_id]
    matched = [(claim, verdict) for claim, verdict in pairs if needle in claim.text]
    assert matched, f"{fixture} 未抽出包含 {needle!r} 的声称：{[c.text for c, _ in pairs]}"
    return matched[0]


def test_three_fixture_dirs_have_readme_and_expected() -> None:
    for name in CLAIMS:
        assert (FIXTURES / name / "README.md").is_file()
        assert (FIXTURES / name / "EXPECTED.md").is_file()


def test_readme_holds_only_real_claims() -> None:
    for name, claim in CLAIMS.items():
        readme = _read(name, "README.md")
        assert claim in readme, f"{name}/README.md 缺固定声称：{claim}"
        hits = [word for word in META_WORDS if word in readme]
        assert not hits, f"{name}/README.md 出现元描述词：{hits}"


def test_expected_md_carries_purpose_and_facts() -> None:
    for name, claim in CLAIMS.items():
        expected = _read(name, "EXPECTED.md")
        assert "## 用途" in expected
        assert "## 被断言的事实" in expected
        assert claim in expected


def test_total_code_lines_under_budget() -> None:
    targets = [
        FIXTURES / "fx-concurrency" / "app.py",
        FIXTURES / "fx-concurrency" / "gunicorn.conf.py",
        FIXTURES / "fx-feature" / "app.py",
        FIXTURES / "fx-testing" / "src" / "calc.py",
        FIXTURES / "fx-testing" / "tests" / "test_calc.py",
    ]
    total = sum(len(p.read_text(encoding="utf-8").splitlines()) for p in targets)
    assert total < 60, f"fixture 代码总量 {total} 行，超出 60 行预算"


def test_fx_concurrency_has_worker_config_without_benchmark() -> None:
    expected = _read("fx-concurrency", "EXPECTED.md")
    assert "`workers = 4`" in expected
    assert "no_evidence" in expected
    assert "workers" in _read("fx-concurrency", "gunicorn.conf.py")
    names = _file_names("fx-concurrency")
    assert not any(hint in names for hint in BENCH_NAME_HINTS), names


def test_fx_feature_has_export_route_and_dependency() -> None:
    expected = _read("fx-feature", "EXPECTED.md")
    assert '@app.get("/export")' in expected
    assert "openpyxl" in expected
    assert '@app.get("/export")' in _read("fx-feature", "app.py")
    assert "openpyxl" in _read("fx-feature", "requirements.txt")


def test_fx_testing_has_two_functions_three_tests_and_no_coverage_report() -> None:
    expected = _read("fx-testing", "EXPECTED.md")
    assert "2 个函数" in expected
    assert "3 个 `def test_`" in expected
    assert "[tool.coverage.run]" in _read("fx-testing", "pyproject.toml")
    assert _read("fx-testing", "src", "calc.py").count("\ndef ") + 1 == 2
    assert _read("fx-testing", "tests", "test_calc.py").count("def test_") == 3
    for report in (".coverage", "coverage.xml", "htmlcov"):
        assert not (FIXTURES / "fx-testing" / report).exists(), report


def test_app_modules_listen_only_under_main_guard() -> None:
    for name in ("fx-concurrency", "fx-feature"):
        before, _, after = _read(name, "app.py").partition('if __name__ == "__main__":')
        assert "app.run(" in after
        assert "app.run(" not in before


def test_end_to_end_verdicts_on_fixtures() -> None:
    for name in CLAIMS:
        claims, verdicts = analyze_repo(FIXTURES / name)
        assert len(claims) == 1, f"{name} 只应抽出一条真实声称：{[c.text for c in claims]}"
        assert len(verdicts) == len(claims)
        assert all(verdict.search_trace for verdict in verdicts), "每条声称都必须留下轨迹"
        assert all(v.status is not Status.contradicted for v in verdicts)


def test_fixtures_three_state_verdicts() -> None:
    concurrency_claim, concurrency_verdict = _verdict_for("fx-concurrency", "500 并发用户")
    assert concurrency_claim.type is ClaimType.concurrency
    assert concurrency_verdict.status is Status.no_evidence
    assert "有配置，无测量" in concurrency_verdict.reason
    assert concurrency_verdict.question

    feature_claim, feature_verdict = _verdict_for("fx-feature", "Excel 导出")
    assert feature_claim.type is ClaimType.feature
    assert feature_verdict.status is Status.supported
    assert feature_verdict.locator is not None

    testing_claim, testing_verdict = _verdict_for("fx-testing", "覆盖率")
    assert testing_claim.type is ClaimType.testing
    assert testing_verdict.status is Status.no_evidence
    assert "有测试，无覆盖结论" in testing_verdict.reason


def _spec_analysis():
    return analyze_spec(FX_SPEC, _read("fx-spec", SPEC_NAME), spec_path=SPEC_NAME)


def _spec_pair(needle: str):
    analysis = _spec_analysis()
    for claim, verdict in zip(analysis.claims, analysis.verdicts):
        if needle in claim.text:
            return claim, verdict
    raise AssertionError(f"fx-spec 未抽出包含 {needle!r} 的需求：{[c.text for c in analysis.claims]}")


def test_fx_spec_dir_has_fixed_files() -> None:
    for name in ("requirements.md", "app.py", "requirements.txt", "EXPECTED.md"):
        assert (FX_SPEC / name).is_file(), name


def test_fx_spec_parse_yields_five_items_with_decidable_distribution() -> None:
    items = parse_spec(_read("fx-spec", SPEC_NAME))
    assert [item.text for item in items] == list(SPEC_TEXTS)
    assert [item.decidable for item in items] == [True, True, True, False, True]
    assert items[3].suggestion == "P95 < 300ms 或 QPS ≥ 500"
    assert items[3].line == 6


def test_fx_spec_analysis_shape_and_metrics_keys() -> None:
    analysis = _spec_analysis()
    assert analysis.repo == "fx-spec"
    assert analysis.spec_path == SPEC_NAME
    assert len(analysis.items) == 5
    assert len(analysis.claims) == 4
    assert len(analysis.verdicts) == 4
    assert [claim.id for claim in analysis.claims] == ["c01", "c02", "c03", "c04"]
    assert set(analysis.metrics) == METRIC_KEYS
    assert len(analysis.overview) == 4


def test_fx_spec_claims_are_external_authority() -> None:
    for claim in _spec_analysis().claims:
        assert claim.authority == "external"
    assert {claim.source for claim in _spec_analysis().claims} == {
        f"{SPEC_NAME}#L3",
        f"{SPEC_NAME}#L4",
        f"{SPEC_NAME}#L5",
        f"{SPEC_NAME}#L7",
    }


def test_fx_spec_claim_types_follow_spec_order() -> None:
    assert [claim.type for claim in _spec_analysis().claims] == [
        ClaimType.feature,
        ClaimType.concurrency,
        ClaimType.feature,
        ClaimType.feature,
    ]


def test_fx_spec_excel_export_is_supported() -> None:
    claim, verdict = _spec_pair("Excel 导出")
    assert claim.type is ClaimType.feature
    assert verdict.status is Status.supported


def test_fx_spec_excel_export_locator_points_at_app_py() -> None:
    _, verdict = _spec_pair("Excel 导出")
    assert verdict.locator is not None
    assert Path(verdict.locator.file).name == "app.py"


def test_fx_spec_concurrency_claim_has_no_evidence() -> None:
    _, verdict = _spec_pair("500 并发用户")
    assert verdict.status is Status.no_evidence
    assert verdict.search_trace


def test_fx_spec_visualization_claim_has_no_evidence() -> None:
    _, verdict = _spec_pair("数据可视化")
    assert verdict.status is Status.no_evidence
    assert verdict.locator is None


def test_fx_spec_app_has_export_and_login_without_visualization() -> None:
    source = _read("fx-spec", "app.py")
    assert '@app.route("/export")' in source
    assert '@app.route("/login")' in source
    assert "def login()" in source
    assert "openpyxl" in source
    lowered = source.lower()
    for hint in ("chart", "plot", "matplotlib", "echarts", "seaborn", "可视化"):
        assert hint not in lowered, hint


def test_fx_spec_report_contains_fixed_anchors(tmp_path) -> None:
    out = tmp_path / "fx-spec.md"
    assert render_spec_to(FX_SPEC, FX_SPEC / SPEC_NAME, out) == out
    text = out.read_text(encoding="utf-8")
    for anchor in (
        "## 需求可判定性预检",
        "P95 < 300ms",
        "## 项目实际是什么",
        "来源：requirements.md#L4",
    ):
        assert anchor in text, anchor

def _spec_report(tmp_path) -> str:
    out = tmp_path / "fx-spec.md"
    render_spec_to(FX_SPEC, FX_SPEC / SPEC_NAME, out)
    return out.read_text(encoding="utf-8")


def test_fx_spec_report_has_single_criteria_line_for_concurrency(tmp_path) -> None:
    criteria = [line for line in _spec_report(tmp_path).splitlines() if line.startswith("- 判据：")]

    assert len(criteria) == 1
    assert criteria[0] == f"- 判据：{CONCURRENCY_CRITERIA}"
    assert "错误率 < 1%" in criteria[0]
    assert "P95 < 1s" in criteria[0]
    assert "行业惯例，需提出人确认" in criteria[0]


def test_fx_spec_criteria_line_sits_between_fix_and_audit_effort(tmp_path) -> None:
    text = _spec_report(tmp_path)
    block = text.split("### 支持 500 并发用户")[1].split("### 用户登录")[0]

    assert block.index("该补什么：") < block.index("- 判据：") < block.index("audit effort：")


def test_fx_spec_criteria_absent_for_non_concurrency_items(tmp_path) -> None:
    text = _spec_report(tmp_path)
    assert text.count("高性能") == 1

    for heading, following in (
        ("### 支持 Excel 导出", "### 支持 500 并发用户"),
        ("### 用户登录", "### 提供数据可视化"),
        ("### 提供数据可视化", "## 未覆盖"),
    ):
        block = text.split(heading)[1].split(following)[0]
        assert "- 判据：" not in block, heading


def test_fx_spec_report_shows_summary_and_routes(tmp_path) -> None:
    analysis = _spec_analysis()
    section = _spec_report(tmp_path).split("## 项目实际是什么")[1].split("## 概览")[0]

    assert analysis.routes == ("GET /export", "GET /login")
    assert analysis.summary == "app.py 暴露 2 个路由；依赖 2 个（flask, openpyxl）；0 个测试文件。"
    assert f"- 一句话：{analysis.summary}" in section
    assert "- 路由：2 个（GET /export, GET /login）" in section


def test_pilot_reports_show_summary_line(tmp_path) -> None:
    for name in ("fx-concurrency", "fx-feature", "fx-testing"):
        out = tmp_path / f"{name}.md"
        assert render_to(FIXTURES / name, out) == out
        section = out.read_text(encoding="utf-8").split("## 项目实际是什么")[1].split("## 概览")[0]
        assert "- 一句话：" in section, name
        assert "个测试文件。" in section, name

    concurrency = (tmp_path / "fx-concurrency.md").read_text(encoding="utf-8")
    assert "- 路由：1 个（GET /healthz）" in concurrency

CHALLENGE = FIXTURES / "fx-challenge"


def _challenge_analysis():
    return analyze_spec(
        CHALLENGE, _read("fx-challenge", "requirements.md"), spec_path="requirements.md"
    )


def _challenge_pair(needle: str):
    analysis = _challenge_analysis()
    for claim, verdict in zip(analysis.claims, analysis.verdicts):
        if needle in claim.text:
            return claim, verdict
    raise AssertionError(f"fx-challenge 未抽出包含 {needle!r} 的需求")


def test_fx_challenge_second_round_upgrades_concurrency_claim() -> None:
    claim, verdict = _challenge_pair("500 并发用户")
    assert claim.type is ClaimType.concurrency
    assert verdict.rounds == 2
    assert verdict.status is Status.supported
    assert verdict.locator is not None
    assert verdict.locator.file == "loadtest/report.log"
    assert "第 2 轮换假设" in verdict.reason


def test_fx_challenge_trace_accumulates_both_rounds() -> None:
    claim, verdict = _challenge_pair("500 并发用户")
    first_round = prober.run(claim, build_index(CHALLENGE), 1)[0]

    probes = [probe.probe for probe in verdict.search_trace]
    assert len(verdict.search_trace) > len(first_round)
    assert "压测结果文件" in probes
    assert any(probe.where for probe in verdict.search_trace)


def test_fx_challenge_first_round_supported_claim_keeps_single_round() -> None:
    _, verdict = _challenge_pair("用户登录")
    assert verdict.status is Status.supported
    assert verdict.rounds == 1


def test_fx_challenge_cli_report_records_rounds_and_effort_sums(tmp_path) -> None:
    out = tmp_path / "fx-challenge.md"
    code = cli.main(
        [
            "spec",
            str(CHALLENGE),
            "--spec",
            str(CHALLENGE / "requirements.md"),
            "--out",
            str(out),
        ]
    )
    assert code == 0
    text = out.read_text(encoding="utf-8")

    assert "换假设：2 轮（第 1 轮查预设来源，其后换假设重搜）" in text
    assert "loadtest/report.log:2" in text
    assert "- 压测结果文件：4 处" in text
    assert "- 本批对未找到的条目最多换假设 2 轮检索（k = max(v.rounds)）。" in text

    total = int(re.search(r"#### 查过 (\d+) 处", text).group(1))
    efforts = sum(int(n) for n in re.findall(r"audit effort：\d+ 类 (\d+) 处", text))
    assert total == efforts


REPORT_CASES = (
    ("fx-concurrency", "analyze", ""),
    ("fx-feature", "analyze", ""),
    ("fx-testing", "analyze", ""),
    ("fx-spec", "spec", "requirements.md"),
    ("fx-challenge", "spec", "requirements.md"),
)


def _cli_report_argv(name: str, mode: str, spec_name: str, out: Path) -> list[str]:
    repo = FIXTURES / name
    if mode == "spec":
        return ["spec", str(repo), "--spec", str(repo / spec_name), "--out", str(out)]
    return ["analyze", str(repo), "--out", str(out)]


@pytest.mark.parametrize("name,mode,spec_name", REPORT_CASES)
def test_committed_reports_match_cli_output(name: str, mode: str, spec_name: str, tmp_path) -> None:
    committed = ROOT / "reports" / f"{name}.md"
    assert committed.is_file(), f"缺少已提交产物 reports/{name}.md"

    out = tmp_path / f"{name}.md"
    assert cli.main(_cli_report_argv(name, mode, spec_name, out)) == 0
    assert out.read_text(encoding="utf-8") == committed.read_text(encoding="utf-8"), (
        f"reports/{name}.md 与当前 CLI 输出不一致，请用 CLI 重新生成"
    )