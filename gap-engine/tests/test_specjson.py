"""C-LLM@1/specjson：gap-spec@1 文档构造、落盘与回读。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from gap_engine.spec import SpecItem, parse_spec
from gap_engine.specjson import (
    PROVIDER_NONE,
    SPEC_SCHEMA,
    build_spec_document,
    load_spec_json,
    write_spec_json,
)

SPEC_TEXT = """\
# 需求清单

- [ ] 支持 Excel 导出
- [ ] 支持 500 并发用户
- [ ] 段落风格自选
- [ ] 高性能
"""


class FakeProvider:
    """鸭子类型 provider：只要求 name 与 complete，不继承 llm 模块的任何类型。"""

    def __init__(self, answer: object = "feature") -> None:
        self.name = "fake-llm"
        self.answer = answer
        self.calls: list[str] = []

    def complete(self, prompt: str) -> str:
        self.calls.append(prompt)
        if isinstance(self.answer, BaseException):
            raise self.answer
        return self.answer  # type: ignore[return-value]


def test_build_document_has_fixed_keys_and_schema() -> None:
    document = build_spec_document(SPEC_TEXT, "requirements.md", None)
    assert list(document) == ["schema", "source", "provider", "items", "dropped"]
    assert document["schema"] == SPEC_SCHEMA == "gap-spec@1"
    assert document["source"] == "requirements.md"
    assert document["provider"] == PROVIDER_NONE == "none"
    assert document["dropped"] == 0


def test_items_match_parse_spec_item_by_item() -> None:
    document = build_spec_document(SPEC_TEXT, "requirements.md", None)
    items = parse_spec(SPEC_TEXT)
    assert document["items"] == [
        {
            "text": item.text,
            "line": item.line,
            "decidable": item.decidable,
            "suggestion": item.suggestion,
        }
        for item in items
    ]
    assert [entry["text"] for entry in document["items"]] == [  # type: ignore[index,union-attr]
        "支持 Excel 导出",
        "支持 500 并发用户",
        "段落风格自选",
        "高性能",
    ]


def test_provider_none_returns_none_provider_field() -> None:
    document = build_spec_document(SPEC_TEXT, "requirements.md", None)
    assert document["provider"] == PROVIDER_NONE


def test_provider_non_none_records_name_and_keeps_items_identical() -> None:
    provider = FakeProvider()
    with_llm = build_spec_document(SPEC_TEXT, "requirements.md", provider)
    without_llm = build_spec_document(SPEC_TEXT, "requirements.md", None)
    assert with_llm["provider"] == "fake-llm"
    assert with_llm["items"] == without_llm["items"]
    assert with_llm["dropped"] == 0
    assert provider.calls, "provider 非空时应参与条目归类"


def test_provider_is_only_asked_about_items_without_keyword_hits() -> None:
    provider = FakeProvider(answer="feature")
    build_spec_document("- 段落风格自选\n", "requirements.md", provider)
    assert provider.calls == ["段落风格自选"]


def test_failing_provider_does_not_change_items_or_dropped() -> None:
    failing = FakeProvider(answer=RuntimeError("boom"))
    document = build_spec_document(SPEC_TEXT, "requirements.md", failing)
    assert document["items"] == build_spec_document(SPEC_TEXT, "requirements.md", None)["items"]
    assert document["dropped"] == 0


def test_non_string_answer_does_not_change_items() -> None:
    odd = FakeProvider(answer=None)
    document = build_spec_document(SPEC_TEXT, "requirements.md", odd)
    assert document["items"] == build_spec_document(SPEC_TEXT, "requirements.md", None)["items"]


def test_write_spec_json_creates_parents_and_ends_with_single_newline(tmp_path: Path) -> None:
    out = tmp_path / "nested" / "deep" / "spec.json"
    returned = write_spec_json(SPEC_TEXT, "requirements.md", out, None)
    assert returned == out
    payload = out.read_text(encoding="utf-8")
    assert payload.endswith("}\n")
    assert not payload.endswith("\n\n")
    assert "支持 Excel 导出" in payload, "ensure_ascii=False：中文原样落盘"
    assert json.loads(payload) == build_spec_document(SPEC_TEXT, "requirements.md", None)


def test_write_spec_json_is_byte_stable_across_runs(tmp_path: Path) -> None:
    first = write_spec_json(SPEC_TEXT, "requirements.md", tmp_path / "a.json", None)
    second = write_spec_json(SPEC_TEXT, "requirements.md", tmp_path / "b.json", None)
    assert first.read_bytes() == second.read_bytes()
    assert b"\r\n" not in first.read_bytes(), "行间用 \\n，不受平台换行影响"


def test_write_spec_json_preserves_key_order_on_disk(tmp_path: Path) -> None:
    out = write_spec_json(SPEC_TEXT, "requirements.md", tmp_path / "spec.json", None)
    assert list(json.loads(out.read_text(encoding="utf-8"))) == [
        "schema",
        "source",
        "provider",
        "items",
        "dropped",
    ]


def test_load_spec_json_round_trips_to_spec_items(tmp_path: Path) -> None:
    out = write_spec_json(SPEC_TEXT, "requirements.md", tmp_path / "spec.json", FakeProvider())
    loaded = load_spec_json(out)
    assert loaded == parse_spec(SPEC_TEXT)
    assert all(isinstance(item, SpecItem) for item in loaded)


def test_load_spec_json_ignores_provider_field(tmp_path: Path) -> None:
    out = tmp_path / "spec.json"
    out.write_text(
        json.dumps(
            {
                "schema": SPEC_SCHEMA,
                "source": "requirements.md",
                "provider": "openai-compatible",
                "items": [
                    {"text": "段落风格自选", "line": 1, "decidable": False, "suggestion": ""}
                ],
                "dropped": 0,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    assert load_spec_json(out) == [
        SpecItem(text="段落风格自选", line=1, decidable=False, suggestion="")
    ]


def _write(tmp_path: Path, payload: object) -> Path:
    out = tmp_path / "spec.json"
    out.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return out


def _valid_payload() -> dict[str, object]:
    return {
        "schema": SPEC_SCHEMA,
        "source": "requirements.md",
        "provider": "none",
        "items": [{"text": "段落风格自选", "line": 1, "decidable": False, "suggestion": "x"}],
        "dropped": 0,
    }


@pytest.mark.parametrize(
    "mutate",
    [
        pytest.param(lambda p: p.__setitem__("schema", "gap-spec@2"), id="bad-schema"),
        pytest.param(lambda p: p.pop("schema"), id="missing-schema"),
        pytest.param(lambda p: p.__setitem__("items", {"text": "x"}), id="items-not-list"),
        pytest.param(lambda p: p.pop("items"), id="missing-items"),
        pytest.param(lambda p: p["items"].append("x"), id="item-not-object"),  # type: ignore[union-attr]
        pytest.param(lambda p: p["items"][0].pop("text"), id="missing-text"),  # type: ignore[index,union-attr]
        pytest.param(lambda p: p["items"][0].__setitem__("text", 1), id="text-not-str"),  # type: ignore[index,union-attr]
        pytest.param(lambda p: p["items"][0].__setitem__("line", "1"), id="line-not-int"),  # type: ignore[index,union-attr]
        pytest.param(lambda p: p["items"][0].__setitem__("line", True), id="line-bool"),  # type: ignore[index,union-attr]
        pytest.param(lambda p: p["items"][0].__setitem__("decidable", "false"), id="decidable-not-bool"),  # type: ignore[index,union-attr]
        pytest.param(lambda p: p["items"][0].pop("suggestion"), id="missing-suggestion"),  # type: ignore[index,union-attr]
        pytest.param(lambda p: p["items"][0].__setitem__("suggestion", None), id="suggestion-not-str"),  # type: ignore[index,union-attr]
    ],
)
def test_load_spec_json_rejects_invalid_payload(tmp_path: Path, mutate) -> None:
    payload = _valid_payload()
    mutate(payload)
    with pytest.raises(ValueError):
        load_spec_json(_write(tmp_path, payload))


def test_load_spec_json_rejects_non_object_top_level(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        load_spec_json(_write(tmp_path, []))


def test_load_spec_json_rejects_broken_json(tmp_path: Path) -> None:
    out = tmp_path / "spec.json"
    out.write_text("{not json", encoding="utf-8")
    with pytest.raises(ValueError):
        load_spec_json(out)


def test_empty_spec_yields_empty_items(tmp_path: Path) -> None:
    document = build_spec_document("# 需求清单\n\n没有列表项\n", "requirements.md", None)
    assert document["items"] == []
    out = write_spec_json("标题\n", "requirements.md", tmp_path / "spec.json", None)
    assert load_spec_json(out) == []