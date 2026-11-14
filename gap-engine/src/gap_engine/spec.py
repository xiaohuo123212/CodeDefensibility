"""需求清单解析与可判定性预检（C-SPEC@1）。

把 Markdown 列表形式的需求清单转成 ``SpecItem``，并给出"能否验收"的判定
与补齐建议；可判定条目再转换成 ``Claim(authority="external")``。
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from .claimer import classify
from .schema import Claim

_ITEM_RE = re.compile(r"^[ \t]*(?:[-*+][ \t]+(?:\[[ xX]\][ \t]+)?|\d+[.)][ \t]+)(\S.*)$")

_MEASURABLE_RE = re.compile(
    r"\d+(?:\.\d+)?\s*(?:%|个|名|人|并发|用户|次|秒|毫秒|ms|s\b|qps|tps|rps)"
    r"|P9\d|P5\d|≥|≤|>=|<=|<|>|至少|不低于|不超过|最多"
)

UNMEASURABLE: dict[str, str] = {
    "美观": "提供视觉规范（配色/字号/间距）并逐项验收",
    "漂亮": "提供视觉规范（配色/字号/间距）并逐项验收",
    "好看": "提供视觉规范（配色/字号/间距）并逐项验收",
    "高性能": "P95 < 300ms 或 QPS ≥ 500",
    "高效": "P95 < 300ms 或 QPS ≥ 500",
    "快速": "P95 < 300ms 或 QPS ≥ 500",
    "稳定": "连续运行 24h 无崩溃，错误率 < 1%",
    "可靠": "连续运行 24h 无崩溃，错误率 < 1%",
    "易用": "新用户在 3 步内完成核心任务",
    "友好": "新用户在 3 步内完成核心任务",
    "丰富": "列出功能条目清单（≥ 5 项）",
    "完善": "给出验收清单 + 测试覆盖率阈值",
    "良好": "分三层 + 模块耦合度指标",
    "优秀": "分三层 + 模块耦合度指标",
    "强大": "列出能力清单与量化上限",
    "简洁": "核心模块 ≤ 8 个，单文件 ≤ 300 行",
    "优雅": "核心模块 ≤ 8 个，单文件 ≤ 300 行",
}

_DEFAULT_SUGGESTION = "建议补充可测量的指标（数字 + 单位 + 判定阈值）"

CONCURRENCY_CRITERIA = "错误率 < 1% 且 P95 < 1s（行业惯例，需提出人确认）"

_THRESHOLD_RE = re.compile(
    r"P9\d|P5\d|错误率|延迟|耗时|毫秒|ms|秒|%|≥|≤|>=|<=|(?<![<>=])<|(?<![<>=])>",
    re.IGNORECASE,
)

_ABILITY_WORDS = ("并发", "qps", "tps", "吞吐")


@dataclass(frozen=True)
class SpecItem:
    text: str
    line: int
    decidable: bool
    suggestion: str


def parse_spec(text: str) -> list[SpecItem]:
    items: list[SpecItem] = []
    seen: set[str] = set()
    for lineno, raw in enumerate(text.splitlines(), start=1):
        match = _ITEM_RE.match(raw)
        if match is None:
            continue
        item_text = match.group(1).strip()
        if len(item_text) < 2 or item_text in seen:
            continue
        seen.add(item_text)
        decidable = is_decidable(item_text)
        items.append(
            SpecItem(
                text=item_text,
                line=lineno,
                decidable=decidable,
                suggestion="" if decidable else suggestion_for(item_text),
            )
        )
    return items


def is_decidable(text: str) -> bool:
    if _MEASURABLE_RE.search(text):
        return True
    return not any(key in text for key in UNMEASURABLE)


def default_criteria(text: str) -> str:
    """可判定但无阈值的并发需求，给出一条可追问的默认判据（纯渲染层用）。"""
    lowered = text.lower()
    if any(word in lowered for word in _ABILITY_WORDS) and not _THRESHOLD_RE.search(text):
        return CONCURRENCY_CRITERIA
    return ""


def suggestion_for(text: str) -> str:
    earliest_key = ""
    earliest_pos = -1
    for key in UNMEASURABLE:
        pos = text.find(key)
        if pos < 0:
            continue
        if earliest_pos < 0 or pos < earliest_pos:
            earliest_key = key
            earliest_pos = pos
    return UNMEASURABLE[earliest_key] if earliest_key else _DEFAULT_SUGGESTION


def claims_from_spec(items: Sequence[SpecItem], spec_path: str) -> list[Claim]:
    claims: list[Claim] = []
    for item in items:
        if not item.decidable:
            continue
        claims.append(
            Claim(
                id=f"c{len(claims) + 1:02d}",
                text=item.text,
                source=f"{spec_path}#L{item.line}",
                type=classify(item.text),
                authority="external",
            )
        )
    return claims