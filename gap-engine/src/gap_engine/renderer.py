"""markdown 报告渲染（C-RENDERER@5：D1 分组渲染 + spec 模式 + 一句话/路由/判据）。

报告里出现的任何计数都由轨迹计算，禁止字面量；逐条按 ``SearchProbe`` 分组，
概览的类数跨 verdict 去重。``render_spec`` 按属性访问 ``SpecAnalysis``，不导入 pipeline。
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from .schema import Claim, Coverage, Status, Verdict
from .spec import default_criteria
from .trace import distinct_scanned


STATUS_CN: dict[Status, str] = {
    Status.supported: "有证据",
    Status.contradicted: "有反证",
    Status.no_evidence: "没找到证据",
}

PILOT_DISCLAIMER = "这是 pilot：报告只说明我查过哪里，不说明你没做过。"
SPEC_DISCLAIMER = "这是 spec 模式：报告只说明我查过哪里，不说明你没做过。"
SPEC_OVERVIEW_HEADING = "## 项目实际是什么"
SPEC_PRECHECK_HEADING = "## 需求可判定性预检"

_LIMITATIONS = [
    "- 本批只跑单轮检索，多轮换假设未启用。",
    "- 只把显式否定声明当反证：没有显式否定时不下断言。",
    "- 缺口判定依赖先验普遍性表（PREVALENCE），尚未用同类项目实测。",
    "- 规则优先，LLM 默认关闭；分类歧义未做消解。",
    "- 报告只反映我查过的位置，不等于你没做过。",
]

_SPEC_LIMITATION = "- spec 模式的补齐物生成与多轮换假设尚未启用。"
_SPEC_LIMITATION_SINGLE_ROUND_ONLY = "- spec 模式的补齐物生成尚未启用。"


def _rounds_cap(verdicts: Sequence[Verdict]) -> int:
    return max((verdict.rounds for verdict in verdicts), default=1)


def _limitations(verdicts: Sequence[Verdict]) -> list[str]:
    k = _rounds_cap(verdicts)
    first = (
        _LIMITATIONS[0]
        if k <= 1
        else f"- 本批对未找到的条目最多换假设 {k} 轮检索（k = max(v.rounds)）。"
    )
    return [first, *_LIMITATIONS[1:]]


def _spec_limitations(verdicts: Sequence[Verdict]) -> list[str]:
    # 多轮已启用时不能再声称"多轮换假设尚未启用"，否则局限段自相矛盾
    tail = _SPEC_LIMITATION if _rounds_cap(verdicts) <= 1 else _SPEC_LIMITATION_SINGLE_ROUND_ONLY
    return [*_limitations(verdicts), tail]


def _label_of(verdict: Verdict) -> str:
    marker = "；缺口："
    reason = verdict.reason or ""
    return reason.rsplit(marker, 1)[1].strip() if marker in reason else ""


def _conclusion_of(verdict: Verdict) -> str:
    if verdict.status is Status.contradicted:
        return "代码里有反证，与要求不一致"
    label = _label_of(verdict)
    text = STATUS_CN.get(verdict.status, "")
    return f"{text}（{label}）" if label else text


def _overview_line(verdicts: list[Verdict], unit: str = "声称") -> str:
    trace = [probe for verdict in verdicts for probe in verdict.search_trace]
    total = sum(probe.scanned for probe in trace)
    classes = len({probe.probe for probe in trace})
    return f"#### 查过 {total} 处（{len(verdicts)} 条{unit}，{classes} 类探测项）"


def _dedup_note(verdicts: list[Verdict]) -> list[str]:
    """补一行去重口径（C-RENDERER@9）：累加数不变，额外给出不同位置数。

    两者相等时不输出，既有报告逐字不变；同一探测项被多条需求重复扫描时
    才出现，避免「查过 N 处」被读成 N 个不同位置。
    """
    trace = [probe for verdict in verdicts for probe in verdict.search_trace]
    total = sum(probe.scanned for probe in trace)
    distinct = distinct_scanned(trace)
    if distinct >= total:
        return []
    return [f"- 其中不同位置 {distinct} 处（同一探测项被多条需求重复扫描时只计一次）", ""]


def _status_line(statuses: list[Status]) -> str:
    counts = Counter(statuses)
    return (
        f"- 有证据 {counts[Status.supported]} 条 / "
        f"没找到证据 {counts[Status.no_evidence]} 条 / "
        f"有反证 {counts[Status.contradicted]} 条"
    )


def _scope_note(pairs: list[tuple[Claim, Verdict]]) -> list[str]:
    """判定域外的条目不进三态统计，单列一行说明，避免与「没找到证据」混淆。"""
    out_of_scope = sum(1 for claim, _ in pairs if claim.out_of_scope)
    return [f"- 其中 {out_of_scope} 条超出判定域，不判定", ""] if out_of_scope else []


def _probe_groups(verdict: Verdict) -> tuple[list[str], list[str]]:
    hit_lines: list[str] = []
    miss_lines: list[str] = []
    for probe in verdict.search_trace:
        if probe.hits > 0:
            hit_lines.append(f"- {probe.probe}：{probe.hits} 处")
            hit_lines.extend(f"  - {item}" for item in probe.where)
        else:
            miss_lines.append(f"- {probe.probe}：0 处（扫过 {probe.scanned} 处）")
    return hit_lines or ["- （无）"], miss_lines or ["- （无）"]


def _claim_block(claim: Claim, verdict: Verdict) -> list[str]:
    if claim.out_of_scope:
        return [
            f"### {claim.text}",
            "",
            f"结论：不判定（{verdict.reason}）",
            "",
            f"该补什么：{verdict.fix}",
            "",
            "audit effort：0 类 0 处",
            "",
        ]
    hit_lines, miss_lines = _probe_groups(verdict)

    conclusion = _conclusion_of(verdict)

    classes = len(verdict.search_trace)
    scanned = sum(probe.scanned for probe in verdict.search_trace)

    lines = [
        f"### {claim.text}",
        "",
        "查到：",
        "",
        *hit_lines,
        "",
        "查过没找到：",
        "",
        *miss_lines,
        "",
        f"结论：{conclusion}",
        "",
    ]

    if verdict.status is Status.contradicted and verdict.locator is not None:
        lines += [f"- 定位：{verdict.locator.as_str()}", ""]

    if verdict.rounds > 1:
        lines += [
            f"换假设：{verdict.rounds} 轮（第 1 轮查预设来源，其后换假设重搜）",
            "",
        ]

    lines += [
        f"会被问：{verdict.question}",
        "",
        f"该补什么：{verdict.fix}",
        "",
    ]

    criteria = default_criteria(claim.text)
    if criteria:
        lines += [f"- 判据：{criteria}", ""]

    lines += [f"audit effort：{classes} 类 {scanned} 处", ""]
    return lines


def _source_block(claim: Claim, verdict: Verdict) -> list[str]:
    block = _claim_block(claim, verdict)
    return [*block[:2], f"来源：{claim.source}", "", *block[2:]]


def _uncovered_lines(pairs: list[tuple[Claim, Verdict]]) -> list[str]:
    uncovered = [
        claim
        for claim, verdict in pairs
        if not claim.out_of_scope
        and (verdict.coverage is Coverage.none or not verdict.search_trace)
    ]
    if not uncovered:
        return ["- 无", ""]
    return [f"- {claim.text}：没有找到任何可查痕迹" for claim in uncovered] + [""]


def _pairs(claims: list[Claim], verdicts: list[Verdict]) -> list[tuple[Claim, Verdict]]:
    claim_by_id = {claim.id: claim for claim in claims}
    return [(claim_by_id[v.claim_id], v) for v in verdicts if v.claim_id in claim_by_id]


def _facts_lines(summary: str, routes: Sequence[str]) -> list[str]:
    lines: list[str] = []
    if summary:
        lines.append(f"- 一句话：{summary}")
    if routes:
        shown = ", ".join(routes[:3])
        tail = f"，等 {len(routes)} 条" if len(routes) > 3 else ""
        lines.append(f"- 路由：{len(routes)} 个（{shown}{tail}）")
    return lines


def render(
    verdicts: list[Verdict],
    claims: list[Claim],
    out: Path,
    repo_name: str,
    *,
    summary: str = "",
    routes: Sequence[str] = (),
) -> Path:
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)

    pairs = _pairs(claims, verdicts)

    lines: list[str] = [
        f"# {repo_name} 对账报告",
        "",
        PILOT_DISCLAIMER,
        "",
    ]

    facts = _facts_lines(summary, routes)
    if facts:
        lines += [SPEC_OVERVIEW_HEADING, "", *facts, ""]

    lines += ["## 概览", ""]

    if not pairs:
        lines += ["未抽取到可判定声称。", ""]
    else:
        lines += [
            _overview_line([verdict for _, verdict in pairs]),
            "",
            *_dedup_note([verdict for _, verdict in pairs]),
            _status_line([v.status for c, v in pairs if not c.out_of_scope]),
            "",
            *_scope_note(pairs),
            "## 逐条",
            "",
        ]
        for claim, verdict in pairs:
            lines += _claim_block(claim, verdict)

    lines += ["## 未覆盖", ""]
    lines += _uncovered_lines(pairs)
    lines += ["## 局限", "", *_limitations([verdict for _, verdict in pairs]), ""]

    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def _precheck_lines(analysis: Any) -> list[str]:
    items = list(analysis.items)
    claims = list(analysis.claims)
    total = len(items)
    decidable = len(claims)
    undecidable = sorted(
        (item for item in items if not getattr(item, "decidable", False)),
        key=lambda item: item.line,
    )

    lines = [
        SPEC_PRECHECK_HEADING,
        "",
        f"共 {total} 条需求，{decidable} 条可判定，{total - decidable} 条无法验收。",
        "",
    ]
    if undecidable:
        for item in undecidable:
            lines.append(
                f'- `{analysis.spec_path}:{item.line}` "{item.text}" → {item.suggestion}'
            )
        lines.append("")
    return lines


def render_spec(
    analysis: Any,
    out: Path,
    *,
    summary: str = "",
    routes: Sequence[str] = (),
) -> Path:
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)

    claims = list(analysis.claims)
    verdicts = list(analysis.verdicts)
    pairs = _pairs(claims, verdicts)

    lines: list[str] = [
        f"# {analysis.repo} 需求对账报告",
        "",
        SPEC_DISCLAIMER,
        "",
        *_precheck_lines(analysis),
        SPEC_OVERVIEW_HEADING,
        "",
    ]

    overview = list(analysis.overview)
    lines += [f"- {row}" for row in overview] if overview else ["- （无）"]
    lines += [*_facts_lines(summary, routes), ""]
    lines += [
        "## 概览",
        "",
        _overview_line(verdicts, "需求"),
        "",
        *_dedup_note(verdicts),
        _status_line([v.status for c, v in pairs if not c.out_of_scope]),
        "",
        *_scope_note(pairs),
        "## 逐条",
        "",
    ]

    if pairs:
        for claim, verdict in pairs:
            lines += _source_block(claim, verdict)
    else:
        lines += ["- （无）", ""]

    lines += ["## 未覆盖", ""]
    lines += _uncovered_lines(pairs)
    lines += ["## 局限", "", *_spec_limitations(verdicts), ""]

    out.write_text("\n".join(lines), encoding="utf-8")
    return out