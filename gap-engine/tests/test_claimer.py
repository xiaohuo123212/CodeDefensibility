"""C-CLAIMER@1/@2：分类优先级、抽取上限、去重与元描述过滤。"""

from __future__ import annotations

from pathlib import Path

from gap_engine.claimer import (
    CAPABILITY_MARKERS,
    META_PREFIXES,
    META_TOKENS,
    QUANT_MARKERS,
    claims_from_readme,
    claims_from_text,
    classify,
    is_meta_sentence,
)
from gap_engine.index import build_index
from gap_engine.schema import ClaimType

FIXTURES = Path(__file__).resolve().parents[1] / "contract" / "fixtures"


def test_marker_constants_cover_capability_and_quant() -> None:
    assert "支持" in CAPABILITY_MARKERS
    assert "built with" in CAPABILITY_MARKERS
    assert "并发" in QUANT_MARKERS
    assert "覆盖率" in QUANT_MARKERS


def test_classify_follows_priority_order() -> None:
    assert classify("支持 500 并发用户，测试覆盖率 80%") is ClaimType.concurrency
    assert classify("响应时间 50ms，性能稳定") is ClaimType.performance
    assert classify("测试覆盖率 80%") is ClaimType.testing
    assert classify("支持 Excel 导出") is ClaimType.feature
    assert classify("支持数据可视化") is ClaimType.feature
    assert classify("使用微服务架构") is ClaimType.architecture
    assert classify("支持十万级数据量") is ClaimType.scale
    assert classify("支持 HTTPS 加密传输") is ClaimType.security


def test_classify_falls_back_to_feature() -> None:
    assert classify("服务足够稳") is ClaimType.feature


def test_classify_uses_llm_only_when_no_keyword_hits() -> None:
    assert classify("服务足够稳", llm=lambda _: "architecture") is ClaimType.architecture
    assert classify("服务足够稳", llm=lambda _: "  Testing ") is ClaimType.testing
    assert classify("服务足够稳", llm=lambda _: "not-a-type") is ClaimType.feature
    assert classify("支持 Excel 导出", llm=lambda _: "security") is ClaimType.feature


def test_classify_survives_llm_failure() -> None:
    def boom(_: str) -> str:
        raise RuntimeError("llm down")

    assert classify("服务足够稳", llm=boom) is ClaimType.feature


def test_claims_from_text_strips_list_markers_and_dedupes() -> None:
    text = "\n".join(
        [
            "# 标题不算声称",
            "- 支持批量导出 Excel 报表",
            "- 支持批量导出 Excel 报表",
            "```bash",
            "pytest -q",
            "```",
            "这是一个普通的说明段落。",
        ]
    )
    claims = claims_from_text(text, "readme")
    assert [c.text for c in claims] == ["支持批量导出 Excel 报表"]
    assert claims[0].id == "c01"
    assert claims[0].source == "readme"
    assert claims[0].checkable is True


def test_claims_from_text_caps_at_max_claims() -> None:
    text = "\n".join(["支持批量导出 Excel 报表", "支持实时同步增量数据", "- 测试覆盖率 80%"])
    claims = claims_from_text(text, "readme", max_claims=2)
    assert [c.text for c in claims] == ["支持批量导出 Excel 报表", "支持实时同步增量数据"]
    assert claims_from_text(text, "readme", max_claims=0) == []
    assert claims_from_text(text, "readme", max_claims=-1) == []


def test_claims_from_readme_reads_fixture_in_order() -> None:
    index = build_index(FIXTURES / "fx-concurrency")
    claims = claims_from_readme(index)
    assert claims, "fx-concurrency 的 README 应抽出声称"
    assert len(claims) <= 5
    assert claims[0].id == "c01"
    assert "500 并发用户" in claims[0].text
    assert claims[0].type is ClaimType.concurrency
    assert all(c.source == "readme" for c in claims)
    assert [c.id for c in claims] == [f"c{i:02d}" for i in range(1, len(claims) + 1)]


def test_claims_from_readme_without_readme_returns_empty(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text("print('hi')\n", encoding="utf-8")
    index = build_index(tmp_path)
    assert claims_from_readme(index) == []

def test_is_meta_sentence_detects_prefixes() -> None:
    assert "因此" in META_PREFIXES
    assert is_meta_sentence("因此代码里支持批量导出") is True
    assert is_meta_sentence("作为回归基线，支持批量导出") is True
    assert is_meta_sentence("本项目仅支持批量导出") is True
    assert is_meta_sentence("- 因此这里支持 500 并发用户") is True


def test_is_meta_sentence_detects_tokens_case_insensitively() -> None:
    assert "no_evidence" in META_TOKENS
    assert is_meta_sentence("服务被标为 SUPPORTED") is True
    assert is_meta_sentence("这条应当被判为 no_evidence") is True
    assert is_meta_sentence("代码里标注 supported 的导出条目") is True


def test_is_meta_sentence_drops_short_sentences() -> None:
    assert is_meta_sentence("支持导出") is True
    assert is_meta_sentence("覆盖率 80%") is True


def test_is_meta_sentence_keeps_real_claims() -> None:
    assert is_meta_sentence("支持 500 并发用户") is False
    assert is_meta_sentence("测试覆盖率 80%") is False
    assert is_meta_sentence("- **测试覆盖率 80%**") is False


def test_claims_from_text_drops_meta_sentences() -> None:
    text = "\n".join(
        [
            "支持 500 并发用户",
            "因此「支持 500 并发用户」应当被判为 no_evidence，并给出缺压测证据的追问",
            "作为抽取器与 Matcher 的回归基线：支持 500 并发用户",
            "所以这里的测试覆盖率不是实测值",
            "代码里标注 supported 的导出条目",
        ]
    )
    claims = claims_from_text(text, "readme")
    assert [c.text for c in claims] == ["支持 500 并发用户"]
    assert claims[0].id == "c01"


def test_ids_stay_contiguous_after_meta_filtering() -> None:
    text = "\n".join(
        [
            "因此这里支持批量导出",
            "支持 500 并发用户",
            "作为回归基线：支持 Excel 导出",
            "测试覆盖率 80%",
        ]
    )
    claims = claims_from_text(text, "readme")
    assert [c.id for c in claims] == ["c01", "c02"]
    assert [c.text for c in claims] == ["支持 500 并发用户", "测试覆盖率 80%"]


def test_meta_filtering_can_empty_the_result() -> None:
    assert claims_from_text("因此这里支持批量导出", "readme") == []