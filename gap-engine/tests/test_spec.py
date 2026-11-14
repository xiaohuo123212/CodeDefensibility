"""C-SPEC@1 / C-SPEC@2：需求清单解析、可判定性预检、Claim 转换与默认判据。"""

from __future__ import annotations

from gap_engine.schema import ClaimType
from gap_engine.spec import (
    CONCURRENCY_CRITERIA,
    UNMEASURABLE,
    SpecItem,
    claims_from_spec,
    default_criteria,
    is_decidable,
    parse_spec,
    suggestion_for,
)

SPEC_TEXT = """\
# 需求清单

- 支持 Excel 导出
- 支持批量上传附件
- [x] 支持用户登录
- 界面美观
1. 支持数据可视化
"""


def test_parse_spec_reads_list_items_with_lines() -> None:
    items = parse_spec(SPEC_TEXT)
    assert [item.text for item in items] == [
        "支持 Excel 导出",
        "支持批量上传附件",
        "支持用户登录",
        "界面美观",
        "支持数据可视化",
    ]
    assert [item.line for item in items] == [3, 4, 5, 6, 7]


def test_parse_spec_supports_all_marker_styles() -> None:
    text = "\n".join(
        [
            "* 支持 Excel 导出",
            "+ 支持批量上传附件",
            "1. 支持用户登录",
            "2) 支持数据可视化",
            "  - [X] 支持定时任务导出",
        ]
    )
    items = parse_spec(text)
    assert [item.text for item in items] == [
        "支持 Excel 导出",
        "支持批量上传附件",
        "支持用户登录",
        "支持数据可视化",
        "支持定时任务导出",
    ]
    assert [item.line for item in items] == [1, 2, 3, 4, 5]


def test_parse_spec_ignores_non_list_lines() -> None:
    assert parse_spec("# 标题\n\n普通段落，描述背景。\n\n") == []
    assert parse_spec("") == []


def test_parse_spec_drops_tiny_and_duplicate_items() -> None:
    text = "\n".join(["- a", "- 支持 Excel 导出", "- 支持 Excel 导出", "- 支持用户登录"])
    items = parse_spec(text)
    assert [item.text for item in items] == ["支持 Excel 导出", "支持用户登录"]
    assert [item.line for item in items] == [2, 4]


def test_parse_spec_decidability_distribution() -> None:
    assert [item.decidable for item in parse_spec(SPEC_TEXT)] == [True, True, True, False, True]
    assert [item.suggestion for item in parse_spec(SPEC_TEXT)][:3] == ["", "", ""]


def test_is_decidable_prefers_measurable_units() -> None:
    assert is_decidable("支持 500 并发用户") is True
    assert is_decidable("响应时间 ≤ 300ms") is True
    assert is_decidable("覆盖率达到 80%") is True
    assert is_decidable("至少支持 3 种格式") is True
    assert is_decidable("支持 Excel 导出") is True
    assert is_decidable("界面美观") is False
    assert is_decidable("系统稳定") is False
    assert is_decidable("性能强大") is False


def test_suggestion_for_uses_earliest_vague_word() -> None:
    assert suggestion_for("界面美观") == "提供视觉规范（配色/字号/间距）并逐项验收"
    assert suggestion_for("系统要高性能") == "P95 < 300ms 或 QPS ≥ 500"
    assert suggestion_for("系统高性能且界面美观") == "P95 < 300ms 或 QPS ≥ 500"
    assert suggestion_for("良好且优秀") == "分三层 + 模块耦合度指标"
    assert suggestion_for("支持 Excel 导出") == "建议补充可测量的指标（数字 + 单位 + 判定阈值）"
    assert len(UNMEASURABLE) == 17


def test_claims_from_spec_only_keeps_decidable_items() -> None:
    items = parse_spec(SPEC_TEXT)
    claims = claims_from_spec(items, "requirements.md")
    assert [claim.id for claim in claims] == ["c01", "c02", "c03", "c04"]
    assert [claim.text for claim in claims] == [
        "支持 Excel 导出",
        "支持批量上传附件",
        "支持用户登录",
        "支持数据可视化",
    ]
    assert [claim.source for claim in claims] == [
        "requirements.md#L3",
        "requirements.md#L4",
        "requirements.md#L5",
        "requirements.md#L7",
    ]
    assert all(claim.type is ClaimType.feature for claim in claims)
    assert all(claim.authority == "external" for claim in claims)
    assert all(claim.checkable is True for claim in claims)
    assert all(claim.out_of_scope is False for claim in claims)


def test_claims_from_spec_returns_empty_for_no_items() -> None:
    assert claims_from_spec([], "requirements.md") == []
    undecidable = [SpecItem(text="界面美观", line=1, decidable=False, suggestion=suggestion_for("界面美观"))]
    assert claims_from_spec(undecidable, "requirements.md") == []

def test_default_criteria_covers_concurrency_without_threshold() -> None:
    for text in ("支持 500 并发用户", "支持 1000 QPS", "support 500 TPS", "吞吐要高"):
        assert default_criteria(text) == CONCURRENCY_CRITERIA, text

    assert "错误率 < 1%" in CONCURRENCY_CRITERIA
    assert "P95 < 1s" in CONCURRENCY_CRITERIA
    assert "行业惯例，需提出人确认" in CONCURRENCY_CRITERIA


def test_default_criteria_empty_when_own_threshold_exists() -> None:
    for text in (
        "支持 500 并发用户，P95 < 1s",
        "支持 500 并发用户，错误率 < 1%",
        "并发 1000，延迟 200ms",
        "并发数 ≤ 500",
        "吞吐 >= 500 次",
    ):
        assert default_criteria(text) == "", text


def test_default_criteria_empty_without_concurrency_semantics() -> None:
    for text in ("高性能", "用户登录", "支持 Excel 导出", "提供数据可视化"):
        assert default_criteria(text) == "", text


def test_default_criteria_does_not_change_decidability() -> None:
    assert is_decidable("支持 500 并发用户") is True
    assert default_criteria("支持 500 并发用户") == CONCURRENCY_CRITERIA
    assert is_decidable("高性能") is False
    assert default_criteria("高性能") == ""