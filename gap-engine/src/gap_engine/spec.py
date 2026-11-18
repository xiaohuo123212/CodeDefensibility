"""需求清单解析与可判定性预检（C-SPEC@1 / C-SPEC@2 / C-SPEC@3）。

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

NEEDS_CRITERIA: dict[str, str] = {
    "合规": "列出适用的法规或标准条款，并给出对应实现位置（file:line）",
    "许可证": "声明项目许可证，并列出依赖许可证清单，确认无冲突",
    "开源协议": "声明项目开源协议，并列出依赖协议清单，确认无冲突",
    "gpl": "确认无 GPL/AGPL 依赖，或隔离为独立进程调用并给出边界",
    "脱敏": "列出敏感字段清单与脱敏规则，并给出至少 1 处实现位置",
    "明文": "列出禁止明文的字段，并给出加密或哈希实现位置",
    "审计": "每个写操作产生审计记录：操作者、时间、对象、变更前后值",
    "留痕": "关键路径留痕覆盖 100%，可回溯到 file:line",
    "不可篡改": "审计记录仅追加，并给出完整性校验方式",
    "热更新": "配置变更无需重启即生效，给出加载位置与生效验证方式",
    "优雅停机": "停机时在途请求在阈值内处理完，给出信号处理位置",
    "灰度": "支持按比例放量，给出开关位置与回滚方式",
    "容灾": "定义 RTO/RPO 数值，并给出切换实现位置",
    "向后兼容": "旧接口契约不变，给出契约测试或版本号证据",
    "租户隔离": "租户数据在查询层强制过滤，给出隔离字段与过滤位置",
    "数据隔离": "租户数据在查询层强制过滤，给出隔离字段与过滤位置",
    "物理隔离": "定义隔离边界（库/表/实例），并给出证据位置",
    "可观测": "关键路径 metric/log/trace 三类覆盖，给出埋点位置",
    "链路追踪": "请求入口生成 trace_id 并全程透传，给出注入位置",
    "国际化": "文案外置到资源文件，给出资源位置与切换入口",
    "无障碍": "对照 WCAG 2.1 AA 逐项核对，并给出可访问性测试",
}

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


def _needs_criteria(text: str) -> str:
    """返回位置最靠前的领域词表命中 key，无命中返回空串。"""
    lowered = text.lower()
    earliest_key = ""
    earliest_pos = -1
    for key in NEEDS_CRITERIA:
        pos = lowered.find(key)
        if pos < 0:
            continue
        if earliest_pos < 0 or pos < earliest_pos:
            earliest_key = key
            earliest_pos = pos
    return earliest_key


def is_decidable(text: str) -> bool:
    if _MEASURABLE_RE.search(text):
        return True
    if any(key in text for key in UNMEASURABLE):
        return False
    return not _needs_criteria(text)


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
    criteria_key = _needs_criteria(text)
    if criteria_key and (earliest_pos < 0 or text.lower().find(criteria_key) < earliest_pos):
        return NEEDS_CRITERIA[criteria_key]
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