"""A 段推演建议：为 ``no_evidence`` 条目生成独立产物（C-LLM@1/advice）。

AI 输出只落在 `--out` 指向的独立 markdown 里：不写 ``Verdict`` 的任何字段、
不产生 ``file:line``、不改变三态结论。prompt 只含需求原文、探测项名称、
已扫处数与缺口标签，源码、路径、``Locator`` 一律不进 prompt。
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .progress import LABEL_ADVICE, PHASE_DONE, PHASE_START, ProgressEvent, ProgressFn
from .schema import Claim, Status, Verdict

if TYPE_CHECKING:
    from .llm import LlmProvider

ADVICE_HEADER = "> AI 推演（非证据，不产生定位，不改变三态结论）"
NO_PROVIDER_LINE = "- 未调用 AI（未配置 GAP_LLM_API_KEY 或未加 --llm），本批次无推演建议。"
ADVICE_LIMIT = 10
EMPTY_ANSWER_LINE = "- （本次调用未返回内容）"
GAP_MARKER = "；缺口："

__all__ = [
    "ADVICE_HEADER",
    "ADVICE_LIMIT",
    "NO_PROVIDER_LINE",
    "advice_targets",
    "render_advice",
]


def advice_targets(analysis: Any) -> list[tuple[Claim, Verdict]]:
    claim_by_id = {claim.id: claim for claim in analysis.claims}
    targets: list[tuple[Claim, Verdict]] = []
    for verdict in analysis.verdicts:
        if verdict.status is not Status.no_evidence:
            continue
        claim = claim_by_id.get(verdict.claim_id)
        if claim is None or claim.out_of_scope:
            continue
        targets.append((claim, verdict))
    targets.sort(key=lambda pair: pair[0].id)
    return targets[:ADVICE_LIMIT]


def render_advice(
    analysis: Any,
    out: Path,
    provider: LlmProvider | None,
    progress: ProgressFn | None = None,
) -> Path:
    lines = [f"# {analysis.repo} 推演建议", "", ADVICE_HEADER, ""]
    if provider is None:
        lines.append(NO_PROVIDER_LINE)
    else:
        targets = advice_targets(analysis)
        total = len(targets)
        for index, (claim, verdict) in enumerate(targets, start=1):
            _emit(progress, PHASE_START, index, total, claim.text, 0.0)
            started = time.perf_counter()
            answer = _ask(provider, _prompt(claim, verdict)).strip()
            _emit(progress, PHASE_DONE, index, total, claim.text, time.perf_counter() - started)
            lines.extend(
                [
                    f"### {claim.text}",
                    "",
                    ADVICE_HEADER,
                    "",
                    answer or EMPTY_ANSWER_LINE,
                    "",
                ]
            )

    target = Path(out)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines).rstrip("\n") + "\n", encoding="utf-8", newline="\n")
    return target


def _emit(
    progress: ProgressFn | None, phase: str, index: int, total: int, text: str, seconds: float
) -> None:
    if progress is None:
        return
    progress(ProgressEvent(phase, index, total, LABEL_ADVICE, text, seconds))


def _ask(provider: LlmProvider, prompt: str) -> str:
    try:
        answer = provider.complete(prompt)
    except Exception:  # R7：调用失败降级为无建议，不得中断推演产物落盘
        return ""
    return answer if isinstance(answer, str) else ""


def _prompt(claim: Claim, verdict: Verdict) -> str:
    probes = "、".join(dict.fromkeys(probe.probe for probe in verdict.search_trace))
    scanned = sum(probe.scanned for probe in verdict.search_trace)
    label = _gap_label(verdict)
    return (
        "你在做代码能力对账的推演环节：规则检索已判定下面这条需求没有找到证据。"
        "请写出验证或补齐该能力的推演建议，三条以内，不要给出文件路径与行号。\n"
        f"需求原文：{claim.text}\n"
        f"已查探测项：{probes or '（无）'}\n"
        f"已扫处数合计：{scanned}\n"
        f"缺口标签：{label or '（未标注）'}\n"
    )


def _gap_label(verdict: Verdict) -> str:
    reason = verdict.reason or ""
    return reason.rsplit(GAP_MARKER, 1)[1].strip() if GAP_MARKER in reason else ""