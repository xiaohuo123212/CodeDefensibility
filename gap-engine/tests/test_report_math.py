"""报告渲染回归（C-RENDERER@4）：分组渲染、概览总计+去重类数、spec 模式八段。"""

from __future__ import annotations

import re
from pathlib import Path
from types import SimpleNamespace

import gap_engine.renderer as renderer
from gap_engine.matcher import CONTRADICTED_FIX, CONTRADICTED_QUESTION_TEMPLATE
from gap_engine.pipeline import analyze_repo, analyze_spec
from gap_engine.renderer import STATUS_CN, render, render_spec
from gap_engine.schema import (
    Claim,
    ClaimType,
    Confidence,
    Coverage,
    Locator,
    SearchProbe,
    Status,
    Verdict,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "contract" / "fixtures"


def _claim(cid: str, text: str, source: str = "readme") -> Claim:
    return Claim(id=cid, text=text, source=source, type=ClaimType.feature)


def _verdict(
    cid: str,
    trace: list[SearchProbe],
    coverage: Coverage = Coverage.partial,
    status: Status = Status.no_evidence,
    rounds: int = 1,
) -> Verdict:
    return Verdict(
        claim_id=cid,
        status=status,
        confidence=Confidence.medium if status is Status.no_evidence else Confidence.high,
        locator=Locator("app.py", 1)
        if status in (Status.supported, Status.contradicted)
        else None,
        coverage=coverage,
        evidence_ids=[],
        reason="",
        search_trace=trace,
        rounds=rounds,
    )


def _item(text: str, line: int, decidable: bool, suggestion: str = "") -> SimpleNamespace:
    return SimpleNamespace(text=text, line=line, decidable=decidable, suggestion=suggestion)


def _analysis(
    items: list[SimpleNamespace],
    claims: list[Claim],
    verdicts: list[Verdict],
    overview: tuple[str, ...] | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        repo="demo",
        spec_path="requirements.md",
        items=tuple(items),
        claims=tuple(claims),
        verdicts=tuple(verdicts),
        overview=overview
        or (
            "文件 3 个，代码 20 行",
            "入口：app.py",
            "依赖：flask",
            "测试：未找到测试文件",
        ),
        metrics={},
    )


def test_claim_block_groups_by_probe(tmp_path: Path) -> None:
    trace = [
        SearchProbe(probe="并发原语", target="t", scanned=2, hits=1, where=["app.py:9"]),
        SearchProbe(probe="压测脚本", target="t", scanned=0, hits=0, where=[]),
        SearchProbe(probe="worker 配置", target="t", scanned=1, hits=1, where=["g.conf:3"]),
    ]
    out = render(
        [_verdict("c01", trace)],
        [_claim("c01", "支持 500 并发用户")],
        tmp_path / "report.md",
        "repo",
    )
    text = out.read_text(encoding="utf-8")

    assert "查到：\n\n- 并发原语：1 处\n  - app.py:9\n- worker 配置：1 处\n  - g.conf:3\n" in text
    assert "查过没找到：\n\n- 压测脚本：0 处（扫过 0 处）\n" in text
    assert "audit effort：3 类 3 处" in text


def test_empty_groups_render_placeholder(tmp_path: Path) -> None:
    out = render(
        [_verdict("c01", [], coverage=Coverage.none)],
        [_claim("c01", "某声称")],
        tmp_path / "report.md",
        "repo",
    )
    text = out.read_text(encoding="utf-8")
    assert "查到：\n\n- （无）\n" in text
    assert "查过没找到：\n\n- （无）\n" in text
    assert "audit effort：0 类 0 处" in text


def test_overview_dedups_probe_classes(tmp_path: Path) -> None:
    shared = [
        SearchProbe(probe="压测脚本", target="t", scanned=2, hits=0, where=[]),
        SearchProbe(probe="并发原语", target="t", scanned=3, hits=1, where=["a.py:1"]),
    ]
    claims = [_claim("c01", "声称一"), _claim("c02", "声称二")]
    verdicts = [_verdict("c01", list(shared)), _verdict("c02", list(shared))]

    out = render(verdicts, claims, tmp_path / "report.md", "repo")
    text = out.read_text(encoding="utf-8")

    assert "#### 查过 10 处（2 条声称，2 类探测项）" in text
    assert "4 类" not in text


def test_per_claim_audit_effort_uses_own_trace(tmp_path: Path) -> None:
    verdicts = [
        _verdict(
            "c01",
            [SearchProbe(probe="结构指标", target="t", scanned=5, hits=0, where=[])],
        ),
        _verdict(
            "c02",
            [
                SearchProbe(probe="结构指标", target="t", scanned=5, hits=0, where=[]),
                SearchProbe(probe="依赖", target="t", scanned=7, hits=0, where=[]),
            ],
        ),
    ]
    claims = [_claim("c01", "声称一"), _claim("c02", "声称二")]
    out = render(verdicts, claims, tmp_path / "report.md", "repo")
    text = out.read_text(encoding="utf-8")

    assert "audit effort：1 类 5 处" in text
    assert "audit effort：2 类 12 处" in text
    assert "#### 查过 17 处（2 条声称，2 类探测项）" in text


def test_fixture_report_groups_and_dedups(tmp_path: Path) -> None:
    claims, verdicts = analyze_repo(FIXTURES / "fx-concurrency")
    out = render(verdicts, claims, tmp_path / "sub" / "report.md", "fx-concurrency")
    text = out.read_text(encoding="utf-8")

    trace = [probe for verdict in verdicts for probe in verdict.search_trace]
    classes = len({probe.probe for probe in trace})
    assert (
        f"#### 查过 {sum(p.scanned for p in trace)} 处"
        f"（{len(verdicts)} 条声称，{classes} 类探测项）"
    ) in text

    assert "audit effort" in text
    assert "这是 pilot：报告只说明我查过哪里，不说明你没做过" in text
    assert "## 未覆盖" in text
    assert "## 局限" in text
    for verdict in verdicts:
        assert f"audit effort：{len(verdict.search_trace)} 类 {sum(p.scanned for p in verdict.search_trace)} 处" in text
        assert STATUS_CN[verdict.status] in text
        for probe in verdict.search_trace:
            heading = f"- {probe.probe}：{probe.hits} 处" if probe.hits else (
                f"- {probe.probe}：0 处（扫过 {probe.scanned} 处）"
            )
            assert heading in text


def test_empty_verdicts_still_render(tmp_path: Path) -> None:
    out = render([], [], tmp_path / "empty.md", "empty-repo")
    text = out.read_text(encoding="utf-8")
    assert "未抽取到可判定声称" in text
    assert "## 未覆盖" in text
    assert "## 局限" in text


def test_render_spec_sections_order(tmp_path: Path) -> None:
    items = [
        _item("支持 Excel 导出", 1, True),
        _item("高性能", 2, False, "P95 < 300ms 或 QPS ≥ 500"),
    ]
    claims = [_claim("c01", "支持 Excel 导出", "requirements.md#L1")]
    verdicts = [
        _verdict(
            "c01",
            [SearchProbe(probe="入口", target="t", scanned=1, hits=1, where=["app.py:3"])],
            coverage=Coverage.full,
        )
    ]
    out = render_spec(_analysis(items, claims, verdicts), tmp_path / "spec.md")
    text = out.read_text(encoding="utf-8")

    anchors = [
        "# demo 需求对账报告",
        "这是 spec 模式：报告只说明我查过哪里，不说明你没做过。",
        "## 需求可判定性预检",
        "## 项目实际是什么",
        "## 概览",
        "## 逐条",
        "## 未覆盖",
        "## 局限",
    ]
    positions = [text.index(anchor) for anchor in anchors]
    assert positions == sorted(positions), positions
    assert len(set(positions)) == len(anchors)


def test_render_spec_precheck_counts_and_suggestions(tmp_path: Path) -> None:
    items = [
        _item("支持 Excel 导出", 1, True),
        _item("用户登录", 2, True),
        _item("高性能", 4, False, "P95 < 300ms 或 QPS ≥ 500"),
        _item("界面美观", 3, False, "提供视觉规范（配色/字号/间距）并逐项验收"),
    ]
    claims = [_claim("c01", "支持 Excel 导出", "requirements.md#L1")]
    out = render_spec(_analysis(items, claims, []), tmp_path / "spec.md")
    text = out.read_text(encoding="utf-8")

    assert "共 4 条需求，1 条可判定，3 条无法验收。" in text
    assert (
        '- `requirements.md:3` "界面美观" → 提供视觉规范（配色/字号/间距）并逐项验收' in text
    )
    assert '- `requirements.md:4` "高性能" → P95 < 300ms 或 QPS ≥ 500' in text
    assert text.index("requirements.md:3") < text.index("requirements.md:4")


def test_render_spec_without_undecidable_has_no_suggestion_list(tmp_path: Path) -> None:
    items = [_item("支持 Excel 导出", 1, True), _item("用户登录", 2, True)]
    claims = [_claim("c01", "支持 Excel 导出", "requirements.md#L1")]
    out = render_spec(_analysis(items, claims, []), tmp_path / "spec.md")
    text = out.read_text(encoding="utf-8")

    assert "共 2 条需求，1 条可判定，1 条无法验收。" in text.split("## 项目实际是什么")[0]

    items2 = [_item("支持 Excel 导出", 1, True)]
    claims2 = [_claim("c01", "支持 Excel 导出", "requirements.md#L1")]
    out2 = render_spec(_analysis(items2, claims2, []), tmp_path / "spec2.md")
    text2 = out2.read_text(encoding="utf-8")
    precheck = text2.split("## 需求可判定性预检")[1].split("## 项目实际是什么")[0]

    assert "共 1 条需求，1 条可判定，0 条无法验收。" in precheck
    assert "→" not in precheck
    assert "- `" not in precheck


def test_render_spec_overview_rows_verbatim(tmp_path: Path) -> None:
    rows = (
        "文件 3 个，代码 20 行",
        "入口：app.py",
        "依赖：flask, openpyxl",
        "测试：1 个测试文件",
    )
    out = render_spec(_analysis([], [], [], overview=rows), tmp_path / "spec.md")
    text = out.read_text(encoding="utf-8")
    section = text.split("## 项目实际是什么")[1].split("## 概览")[0]

    for row in rows:
        assert f"- {row}" in section


def test_render_spec_source_line_and_empty_verdicts(tmp_path: Path) -> None:
    empty = render_spec(_analysis([], [], []), tmp_path / "empty-spec.md")
    empty_text = empty.read_text(encoding="utf-8")
    assert "#### 查过 0 处（0 条需求，0 类探测项）" in empty_text
    assert "## 逐条\n\n- （无）\n" in empty_text

    claims = [_claim("c01", "支持 Excel 导出", "requirements.md#L4")]
    verdicts = [
        _verdict(
            "c01",
            [SearchProbe(probe="入口", target="t", scanned=1, hits=1, where=["app.py:3"])],
            coverage=Coverage.full,
        )
    ]
    out = render_spec(_analysis([], claims, verdicts), tmp_path / "spec.md")
    text = out.read_text(encoding="utf-8")
    assert "### 支持 Excel 导出\n\n来源：requirements.md#L4\n\n查到：" in text


def test_render_spec_limitations_append_spec_line(tmp_path: Path) -> None:
    out = render_spec(_analysis([], [], []), tmp_path / "spec.md")
    text = out.read_text(encoding="utf-8")
    limitations = text.split("## 局限")[1]

    assert "- spec 模式的补齐物生成与多轮换假设尚未启用。" in limitations
    assert "- 本批只跑单轮检索，多轮换假设未启用。" in limitations


def test_renderer_does_not_import_pipeline() -> None:
    source = Path(renderer.__file__).read_text(encoding="utf-8")
    assert "from .pipeline" not in source
    assert "import gap_engine.pipeline" not in source

def _overview_of(text: str) -> str:
    return next(line for line in text.splitlines() if line.startswith("#### 查过"))


def _audit_effort_sum(text: str) -> int:
    return sum(int(match) for match in re.findall(r"audit effort：\d+ 类 (\d+) 处", text))


def test_concurrency_overview_states_total_and_dedup_classes(tmp_path: Path) -> None:
    claims, verdicts = analyze_repo(FIXTURES / "fx-concurrency")
    out = render(verdicts, claims, tmp_path / "report.md", "fx-concurrency")
    text = out.read_text(encoding="utf-8")

    assert len(verdicts) == 1
    assert (
        _overview_of(text) == f"#### 查过 {_audit_effort_sum(text)} 处（1 条声称，6 类探测项）"
    )


def test_spec_overview_is_total_of_per_claim_efforts(tmp_path: Path) -> None:
    spec = FIXTURES / "fx-spec" / "requirements.md"
    analysis = analyze_spec(
        FIXTURES / "fx-spec", spec.read_text(encoding="utf-8"), spec_path=spec.name
    )
    out = render_spec(analysis, tmp_path / "spec.md")
    text = out.read_text(encoding="utf-8")

    assert len(analysis.verdicts) == 4
    assert (
        _overview_of(text) == f"#### 查过 {_audit_effort_sum(text)} 处（4 条需求，10 类探测项）"
    )

def test_claim_block_puts_criteria_between_fix_and_audit_effort(tmp_path: Path) -> None:
    trace = [SearchProbe(probe="压测脚本", target="t", scanned=2, hits=0, where=[])]
    out = render(
        [_verdict("c01", trace)],
        [_claim("c01", "支持 500 并发用户")],
        tmp_path / "report.md",
        "repo",
    )
    text = out.read_text(encoding="utf-8")

    assert text.count("- 判据：") == 1
    assert (
        text.index("该补什么：")
        < text.index("- 判据：错误率 < 1% 且 P95 < 1s（行业惯例，需提出人确认）")
        < text.index("audit effort：")
    )


def test_claim_block_omits_criteria_without_threshold_gap(tmp_path: Path) -> None:
    claims = [_claim("c01", "用户登录"), _claim("c02", "支持 Excel 导出")]
    verdicts = [
        _verdict("c01", [], coverage=Coverage.none),
        _verdict("c02", [], coverage=Coverage.none),
    ]
    out = render(verdicts, claims, tmp_path / "report.md", "repo")

    assert "- 判据：" not in out.read_text(encoding="utf-8")


def test_criteria_line_does_not_change_audit_effort(tmp_path: Path) -> None:
    trace = [SearchProbe(probe="压测脚本", target="t", scanned=2, hits=0, where=[])]
    out = render(
        [_verdict("c01", trace)],
        [_claim("c01", "支持 500 并发用户")],
        tmp_path / "report.md",
        "repo",
    )
    text = out.read_text(encoding="utf-8")

    assert "audit effort：1 类 2 处" in text
    assert _overview_of(text) == "#### 查过 2 处（1 条声称，1 类探测项）"


def test_render_puts_facts_lines_before_overview(tmp_path: Path) -> None:
    summary = "app.py 暴露 1 个路由；依赖 1 个（flask）；0 个测试文件。"
    out = render(
        [_verdict("c01", [], coverage=Coverage.none)],
        [_claim("c01", "某声称")],
        tmp_path / "report.md",
        "repo",
        summary=summary,
        routes=("GET /healthz",),
    )
    text = out.read_text(encoding="utf-8")
    section = text.split("## 项目实际是什么")[1].split("## 概览")[0]

    assert f"- 一句话：{summary}" in section
    assert "- 路由：1 个（GET /healthz）" in section
    assert text.index("## 项目实际是什么") < text.index("## 概览")


def test_render_omits_facts_section_when_empty(tmp_path: Path) -> None:
    out = render([], [], tmp_path / "empty.md", "empty-repo")
    text = out.read_text(encoding="utf-8")

    assert "## 项目实际是什么" not in text
    assert "- 一句话：" not in text
    assert "- 路由：" not in text


def test_render_routes_line_lists_at_most_three_names(tmp_path: Path) -> None:
    three = render([], [], tmp_path / "three.md", "repo", routes=("GET /a", "GET /b", "GET /c"))
    assert "- 路由：3 个（GET /a, GET /b, GET /c）\n" in three.read_text(encoding="utf-8")

    four = render(
        [], [], tmp_path / "four.md", "repo", routes=("GET /a", "GET /b", "GET /c", "GET /d")
    )
    assert "- 路由：4 个（GET /a, GET /b, GET /c，等 4 条）" in four.read_text(encoding="utf-8")


def test_render_spec_appends_facts_lines_after_overview_rows(tmp_path: Path) -> None:
    rows = ("文件 3 个，代码 20 行", "入口：app.py", "依赖：flask", "测试：未找到测试文件")
    summary = "app.py 暴露 2 个路由；依赖 1 个（flask）；0 个测试文件。"
    out = render_spec(
        _analysis([], [], [], overview=rows),
        tmp_path / "spec.md",
        summary=summary,
        routes=("GET /export", "GET /login"),
    )
    section = out.read_text(encoding="utf-8").split("## 项目实际是什么")[1].split("## 概览")[0]
    lines = [line for line in section.splitlines() if line.startswith("- ")]

    assert lines[:4] == [f"- {row}" for row in rows]
    assert lines[4] == f"- 一句话：{summary}"
    assert lines[5] == "- 路由：2 个（GET /export, GET /login）"


def test_render_spec_omits_facts_lines_when_empty(tmp_path: Path) -> None:
    out = render_spec(_analysis([], [], []), tmp_path / "spec.md")
    text = out.read_text(encoding="utf-8")

    assert "- 一句话：" not in text
    assert "- 路由：" not in text

def test_claim_block_inserts_rounds_line_between_conclusion_and_question(
    tmp_path: Path,
) -> None:
    trace = [
        SearchProbe(probe="压测脚本", target="t", scanned=1, hits=0, where=[]),
        SearchProbe(probe="压测结果文件", target="t", scanned=1, hits=1, where=["loadtest/report.log:2"]),
    ]
    out = render(
        [_verdict("c01", trace, status=Status.supported, rounds=2)],
        [_claim("c01", "支持 500 并发用户")],
        tmp_path / "report.md",
        "repo",
    )
    text = out.read_text(encoding="utf-8")

    rounds_line = "换假设：2 轮（第 1 轮查预设来源，其后换假设重搜）"
    assert rounds_line in text
    assert text.index("结论：") < text.index(rounds_line) < text.index("会被问：")
    assert text.index("audit effort：") > text.index("会被问：")


def test_claim_block_omits_rounds_line_for_single_round(tmp_path: Path) -> None:
    trace = [SearchProbe(probe="压测脚本", target="t", scanned=1, hits=0, where=[])]
    out = render(
        [_verdict("c01", trace)],
        [_claim("c01", "支持 500 并发用户")],
        tmp_path / "report.md",
        "repo",
    )

    assert "换假设：" not in out.read_text(encoding="utf-8")


def test_rounds_line_does_not_change_audit_effort_or_overview(tmp_path: Path) -> None:
    trace = [
        SearchProbe(probe="压测脚本", target="t", scanned=3, hits=0, where=[]),
        SearchProbe(probe="压测结果文件", target="t", scanned=2, hits=1, where=["r.log:1"]),
    ]
    single = render(
        [_verdict("c01", trace[:1])],
        [_claim("c01", "支持 500 并发用户")],
        tmp_path / "single.md",
        "repo",
    )
    multi = render(
        [_verdict("c01", trace, status=Status.supported, rounds=2)],
        [_claim("c01", "支持 500 并发用户")],
        tmp_path / "multi.md",
        "repo",
    )
    single_text = single.read_text(encoding="utf-8")
    multi_text = multi.read_text(encoding="utf-8")

    assert "audit effort：2 类 5 处" in multi_text
    assert _overview_of(multi_text) == "#### 查过 5 处（1 条声称，2 类探测项）"
    assert "audit effort：1 类 3 处" in single_text
    assert "换假设：" not in single_text


def test_limitations_follow_max_rounds(tmp_path: Path) -> None:
    trace = [SearchProbe(probe="压测脚本", target="t", scanned=1, hits=0, where=[])]
    single = render(
        [_verdict("c01", trace)],
        [_claim("c01", "支持 500 并发用户")],
        tmp_path / "single.md",
        "repo",
    ).read_text(encoding="utf-8")
    multi = render(
        [_verdict("c01", trace, rounds=2)],
        [_claim("c01", "支持 500 并发用户")],
        tmp_path / "multi.md",
        "repo",
    ).read_text(encoding="utf-8")

    assert "- 本批只跑单轮检索，多轮换假设未启用。" in single.split("## 局限")[1]
    assert "最多换假设" not in single
    assert "- 本批对未找到的条目最多换假设 2 轮检索（k = max(v.rounds)）。" in multi.split(
        "## 局限"
    )[1]
    assert "本批只跑单轮检索" not in multi


def test_spec_limitations_follow_max_rounds(tmp_path: Path) -> None:
    trace = [SearchProbe(probe="压测脚本", target="t", scanned=1, hits=0, where=[])]
    claims = [_claim("c01", "支持 500 并发用户")]
    multi = render_spec(
        _analysis(
            [_item("支持 500 并发用户", 1, True)],
            claims,
            [_verdict("c01", trace, rounds=3)],
        ),
        tmp_path / "spec.md",
    ).read_text(encoding="utf-8")
    limitations = multi.split("## 局限")[1]

    assert "- 本批对未找到的条目最多换假设 3 轮检索（k = max(v.rounds)）。" in limitations
    assert "- spec 模式的补齐物生成尚未启用。" in limitations
    assert "多轮换假设尚未启用" not in limitations


def test_fx_concurrency_stays_no_evidence_with_two_rounds(tmp_path: Path) -> None:
    claims, verdicts = analyze_repo(FIXTURES / "fx-concurrency")
    out = render(verdicts, claims, tmp_path / "report.md", "fx-concurrency")
    text = out.read_text(encoding="utf-8")

    assert len(verdicts) == 1
    assert verdicts[0].status is Status.no_evidence
    assert verdicts[0].rounds == 2
    assert "换假设：2 轮（第 1 轮查预设来源，其后换假设重搜）" in text
    assert "结论：没找到证据" in text
    assert "- 本批对未找到的条目最多换假设 2 轮检索（k = max(v.rounds)）。" in text.split("## 局限")[1]

def test_max_rounds_is_clamped_to_one_through_three() -> None:
    repo = FIXTURES / "fx-concurrency"
    _, zero = analyze_repo(repo, max_rounds=0)
    _, one = analyze_repo(repo, max_rounds=1)
    _, three = analyze_repo(repo, max_rounds=3)
    _, oversized = analyze_repo(repo, max_rounds=99)

    assert [v.rounds for v in zero] == [1]
    assert [v.rounds for v in one] == [1]
    assert [v.rounds for v in three] == [2]
    assert [v.rounds for v in oversized] == [v.rounds for v in three]
    assert all(v.status is Status.no_evidence for v in three)


def test_spec_max_rounds_is_clamped_too() -> None:
    spec = FIXTURES / "fx-spec" / "requirements.md"
    text = spec.read_text(encoding="utf-8")

    limited = analyze_spec(FIXTURES / "fx-spec", text, spec_path=spec.name, max_rounds=1)
    oversized = analyze_spec(FIXTURES / "fx-spec", text, spec_path=spec.name, max_rounds=99)

    assert all(v.rounds == 1 for v in limited.verdicts)
    assert max(v.rounds for v in oversized.verdicts) == 2


def test_single_round_report_has_no_switch_line(tmp_path: Path) -> None:
    claims, verdicts = analyze_repo(FIXTURES / "fx-concurrency", max_rounds=1)
    out = render(verdicts, claims, tmp_path / "single.md", "fx-concurrency")
    text = out.read_text(encoding="utf-8")

    assert all(v.rounds == 1 for v in verdicts)
    assert "换假设：" not in text
    assert "- 本批只跑单轮检索，多轮换假设未启用。" in text.split("## 局限")[1]
    assert _overview_of(text) == f"#### 查过 {_audit_effort_sum(text)} 处（1 条声称，5 类探测项）"

def test_claim_block_contradicted_uses_fixed_conclusion_and_locator(tmp_path: Path) -> None:
    trace = [
        SearchProbe(probe="否定/未实现声明", target="t", scanned=3, hits=1, where=["app.py:9"]),
    ]
    verdict = _verdict("c01", trace, status=Status.contradicted, coverage=Coverage.full)
    verdict.reason = "代码里有反证：导出功能暂未实现；缺口：该改"
    verdict.question = CONTRADICTED_QUESTION_TEMPLATE.format(text="支持 Excel 导出")
    verdict.fix = CONTRADICTED_FIX

    out = render([verdict], [_claim("c01", "支持 Excel 导出")], tmp_path / "report.md", "repo")
    text = out.read_text(encoding="utf-8")

    assert "结论：代码里有反证，与要求不一致" in text
    assert "（该改）" not in text
    assert "- 定位：app.py:1" in text
    assert text.index("结论：") < text.index("- 定位：") < text.index("会被问：")
    assert CONTRADICTED_FIX in text
    assert CONTRADICTED_QUESTION_TEMPLATE.format(text="支持 Excel 导出") in text


def test_contradicted_block_has_no_rounds_line(tmp_path: Path) -> None:
    trace = [SearchProbe(probe="否定/未实现声明", target="t", scanned=1, hits=1, where=["app.py:9"])]
    out = render(
        [_verdict("c01", trace, status=Status.contradicted)],
        [_claim("c01", "支持 Excel 导出")],
        tmp_path / "report.md",
        "repo",
    )
    text = out.read_text(encoding="utf-8")

    assert "换假设：" not in text
    assert "- 定位：app.py:1" in text

def test_overview_adds_distinct_positions_only_when_shared(tmp_path: Path) -> None:
    shared = SearchProbe(
        probe="相关实现", target="按模块划分的实现文件", scanned=10, hits=0, where=[]
    )
    claims = [_claim("c01", "需求一"), _claim("c02", "需求二")]
    verdicts = [_verdict("c01", [shared]), _verdict("c02", [shared])]

    out = render_spec(_analysis([], claims, verdicts), tmp_path / "spec.md")
    text = out.read_text(encoding="utf-8")

    assert _overview_of(text) == "#### 查过 20 处（2 条需求，1 类探测项）"
    assert "- 其中不同位置 10 处（同一探测项被多条需求重复扫描时只计一次）\n" in text


def test_overview_omits_distinct_line_when_no_duplicate(tmp_path: Path) -> None:
    trace = [SearchProbe(probe="压测脚本", target="t", scanned=5, hits=0, where=[])]
    out = render([_verdict("c01", trace)], [_claim("c01", "某声称")], tmp_path / "r.md", "repo")
    text = out.read_text(encoding="utf-8")

    assert _overview_of(text) == "#### 查过 5 处（1 条声称，1 类探测项）"
    assert "其中不同位置" not in text