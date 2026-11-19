"""C-LLM@1/specjson@2/@4/@5：gap-spec@1 文档构造、不可判定条目判据生成、落盘与回读。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from gap_engine.progress import LABEL_CRITERIA, ProgressEvent
from gap_engine.spec import SpecItem, parse_spec
from gap_engine.specjson import (
    CRITERIA_MAX_CHARS,
    CRITERIA_PROMPT,
    PROVIDER_NONE,
    SPEC_SCHEMA,
    _CRITERIA_CHECK_RE,
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

CRITERIA = "P95 < 300ms 且错误率 < 1%"

FX_SPEC = (
    Path(__file__).resolve().parents[1]
    / "contract"
    / "fixtures"
    / "fx-spec"
    / "requirements.md"
)


class FakeProvider:
    """鸭子类型 provider：只要求 name 与 complete，不继承 llm 模块的任何类型。"""

    def __init__(self, answer: object = CRITERIA) -> None:
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


def test_constants_are_frozen() -> None:
    assert CRITERIA_MAX_CHARS == 200
    assert "{text}" in CRITERIA_PROMPT
    assert CRITERIA_PROMPT.endswith("需求原文：{text}")


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


def test_provider_non_none_records_name_and_overrides_only_criteria() -> None:
    provider = FakeProvider()
    with_llm = build_spec_document(SPEC_TEXT, "requirements.md", provider)
    without_llm = build_spec_document(SPEC_TEXT, "requirements.md", None)
    assert with_llm["provider"] == "fake-llm"
    assert with_llm["dropped"] == 0

    before = without_llm["items"]
    after = with_llm["items"]
    assert isinstance(before, list) and isinstance(after, list)
    assert [
        (entry["text"], entry["line"], entry["decidable"]) for entry in after
    ] == [(entry["text"], entry["line"], entry["decidable"]) for entry in before]
    changed = [
        (old["text"], old["suggestion"], new["suggestion"])
        for old, new in zip(before, after)
        if old["suggestion"] != new["suggestion"]
    ]
    assert changed == [("高性能", "P95 < 300ms 或 QPS ≥ 500", CRITERIA)]


def test_provider_asked_once_per_undecidable_item_in_fx_spec() -> None:
    text = FX_SPEC.read_text(encoding="utf-8")
    decidable = [item.text for item in parse_spec(text) if item.decidable]
    undecidable = [item.text for item in parse_spec(text) if not item.decidable]
    assert len(parse_spec(text)) == 5
    assert undecidable == ["高性能"]

    provider = FakeProvider()
    build_spec_document(text, FX_SPEC.name, provider)

    assert len(provider.calls) == 1, "fx-spec 恰 1 条不可判定 → 恰好 1 次模型调用"
    assert provider.calls == [CRITERIA_PROMPT.format(text="高性能")]
    for text_of_decidable in decidable:
        assert not any(text_of_decidable in prompt for prompt in provider.calls)


def test_prompt_contains_only_requirement_text() -> None:
    provider = FakeProvider()
    build_spec_document("- 高性能\n", "requirements.md", provider)
    assert provider.calls == [CRITERIA_PROMPT.format(text="高性能")]
    prompt = provider.calls[0]
    for leaked in ("requirements.md", "gap_engine", ".py", "L1", "probe", "Locator"):
        assert leaked not in prompt


def test_criteria_takes_first_non_empty_line() -> None:
    provider = FakeProvider(answer="\n\n   吞吐 ≥ 500 QPS  \n第二行不给\n")
    document = build_spec_document("- 高性能\n", "requirements.md", provider)
    assert document["items"] == [
        {"text": "高性能", "line": 1, "decidable": False, "suggestion": "吞吐 ≥ 500 QPS"}
    ]


def test_criteria_truncated_to_max_chars() -> None:
    provider = FakeProvider(answer="长" * (CRITERIA_MAX_CHARS + 50) + "，P95 < 300ms")
    document = build_spec_document("- 高性能\n", "requirements.md", provider)
    suggestion = document["items"][0]["suggestion"]  # type: ignore[index]
    assert suggestion == "长" * CRITERIA_MAX_CHARS
    assert len(suggestion) == CRITERIA_MAX_CHARS


# ---------- C-LLM@1/specjson@4/@5 判据校验 ----------


def test_criteria_check_re_matches_threshold_and_file_locator_forms() -> None:
    for text in (
        "支持 500 并发用户",
        "延迟 ≤ 200ms",
        "P95 < 1s",
        "覆盖 3 类场景",
        "见 file:src/a.py:9",
    ):
        assert _CRITERIA_CHECK_RE.search(text), text
    for text in ("系统满足等保三级安全要求", "系统支持配置热更新功能", ""):
        assert _CRITERIA_CHECK_RE.search(text) is None, text


def test_criteria_without_threshold_or_locator_keeps_rule_suggestion() -> None:
    rule_items = build_spec_document("- 高性能\n", "requirements.md", None)["items"]
    for answer in ("系统满足等保三级安全要求\n", "系统支持配置热更新功能\n", "高性能\n"):
        document = build_spec_document("- 高性能\n", "requirements.md", FakeProvider(answer))
        assert document["items"] == rule_items, answer


def test_criteria_skips_non_matching_lines_before_accepted_line() -> None:
    provider = FakeProvider(answer="系统满足等保三级安全要求\nP95 < 300ms，错误率 < 1%\n")
    document = build_spec_document("- 高性能\n", "requirements.md", provider)
    assert document["items"] == [
        {
            "text": "高性能",
            "line": 1,
            "decidable": False,
            "suggestion": "P95 < 300ms，错误率 < 1%",
        }
    ]


def test_criteria_accepts_file_locator_answer() -> None:
    provider = FakeProvider(answer="审计开关见 file:config/audit.yaml")
    document = build_spec_document("- 高性能\n", "requirements.md", provider)
    assert document["items"][0]["suggestion"] == "审计开关见 file:config/audit.yaml"  # type: ignore[index]


def test_criteria_drops_threshold_appended_to_restated_requirement() -> None:
    """真模型实测缺陷：把需求原样复述，再在末尾附会一个无关阈值。"""
    spec = "- 系统支持配置热更新功能\n"
    rule_items = build_spec_document(spec, "requirements.md", None)["items"]
    for answer in (
        "系统支持配置热更新功能，更新频率不低于1次/天。",
        "系统支持配置热更新功能，更新频率不低于1次/天",
        "系统支持配置热更新功能更新频率不低于1次/天。",
        "系统支持配置热更新功能。",
    ):
        document = build_spec_document(spec, "requirements.md", FakeProvider(answer))
        assert document["items"] == rule_items, answer


def test_criteria_strips_restated_prefix_and_keeps_the_clarification() -> None:
    """「原文 + 真澄清」是合格改写：只丢复述那半句，不把有用的残量一起丢掉。"""
    spec = "- 系统支持配置热更新功能\n"
    provider = FakeProvider("系统支持配置热更新功能，配置变更后5秒内生效，无需重启")
    document = build_spec_document(spec, "requirements.md", provider)
    assert document["items"][0]["suggestion"] == "配置变更后5秒内生效，无需重启"  # type: ignore[index]


def test_criteria_rejects_reordered_restatement_with_threshold() -> None:
    """换语序、加主语后的复述仍与原文高度重合，附一个阈值也不能放行。"""
    spec = "- 配置支持热更新\n"
    rule_items = build_spec_document(spec, "requirements.md", None)["items"]
    for answer in (
        "系统支持配置热更新功能，5秒内生效",
        "系统支持配置热更新功能",
    ):
        document = build_spec_document(spec, "requirements.md", FakeProvider(answer))
        assert document["items"] == rule_items, answer


def test_criteria_rejects_judgement_off_the_requirement_topic() -> None:
    """有阈值却没命中需求任何一个核心词，就是另起炉灶，回落规则兜底。"""
    spec = "- 支持灰度发布\n"
    rule_items = build_spec_document(spec, "requirements.md", None)["items"]
    document = build_spec_document(spec, "requirements.md", FakeProvider("系统支持5%流量分发测试"))
    assert document["items"] == rule_items


def test_criteria_accepts_short_requirement_with_stacked_generic_prefix() -> None:
    """「系统应具备高性能」剥掉多层骨架词后只剩短核心，不该被判离题。"""
    spec = "- 系统应具备高性能\n"
    provider = FakeProvider("响应时间小于100毫秒")
    document = build_spec_document(spec, "requirements.md", provider)
    assert document["items"][0]["suggestion"] == "响应时间小于100毫秒"  # type: ignore[index]


def test_criteria_accepts_rewrite_that_drops_the_original_wording() -> None:
    spec = "- 系统支持配置热更新功能\n"
    provider = FakeProvider("配置变更无需重启即生效，生效时间小于1秒")
    document = build_spec_document(spec, "requirements.md", provider)
    assert document["items"][0]["suggestion"] == "配置变更无需重启即生效，生效时间小于1秒"  # type: ignore[index]


def test_blank_answer_keeps_rule_suggestion() -> None:
    for answer in ("", "\n\n   \n"):
        document = build_spec_document("- 高性能\n", "requirements.md", FakeProvider(answer))
        assert document["items"] == build_spec_document("- 高性能\n", "requirements.md", None)["items"]


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


def test_write_spec_json_persists_criteria_to_disk(tmp_path: Path) -> None:
    out = write_spec_json(SPEC_TEXT, "requirements.md", tmp_path / "spec.json", FakeProvider())
    on_disk = json.loads(out.read_text(encoding="utf-8"))
    assert on_disk["provider"] == "fake-llm"
    suggestions = {entry["text"]: entry["suggestion"] for entry in on_disk["items"]}
    assert suggestions["高性能"] == CRITERIA
    assert "P95 < 300ms 或 QPS ≥ 500" not in out.read_text(encoding="utf-8")


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
    out = write_spec_json(SPEC_TEXT, "requirements.md", tmp_path / "spec.json", None)
    loaded = load_spec_json(out)
    assert loaded == parse_spec(SPEC_TEXT)
    assert all(isinstance(item, SpecItem) for item in loaded)


def test_load_spec_json_reads_back_persisted_criteria_without_calling_model(
    tmp_path: Path,
) -> None:
    out = write_spec_json(SPEC_TEXT, "requirements.md", tmp_path / "spec.json", FakeProvider())
    loaded = load_spec_json(out)
    by_text = {item.text: item for item in loaded}
    assert by_text["高性能"].suggestion == CRITERIA
    assert by_text["高性能"].decidable is False
    assert [item.text for item in loaded] == [item.text for item in parse_spec(SPEC_TEXT)]


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

# ---------- C-LLM@1/specjson@3 progress ----------


def test_progress_emits_paired_events_per_model_call() -> None:
    provider = FakeProvider()
    events: list[ProgressEvent] = []
    total = sum(1 for item in parse_spec(SPEC_TEXT) if not item.decidable)

    build_spec_document(SPEC_TEXT, "requirements.md", provider, events.append)

    starts = [event for event in events if event.phase == "start"]
    dones = [event for event in events if event.phase == "done"]
    assert total >= 1
    assert len(provider.calls) == len(starts) == len(dones) == total
    assert [event.phase for event in events] == ["start", "done"] * total
    assert [event.index for event in starts] == list(range(1, total + 1))
    assert all(event.total == total for event in events)
    assert all(event.label == LABEL_CRITERIA for event in events)
    assert all(event.seconds == 0.0 for event in starts)
    assert all(event.seconds >= 0.0 for event in dones)


def test_progress_absent_without_provider() -> None:
    events: list[ProgressEvent] = []
    build_spec_document(SPEC_TEXT, "requirements.md", None, events.append)
    assert events == []


def test_progress_absent_when_callback_missing() -> None:
    provider = FakeProvider()
    document = build_spec_document(SPEC_TEXT, "requirements.md", provider)
    assert len(provider.calls) == sum(
        1 for item in parse_spec(SPEC_TEXT) if not item.decidable
    )
    assert document["provider"] == "fake-llm"


def test_progress_does_not_change_payload_bytes(tmp_path: Path) -> None:
    events: list[ProgressEvent] = []
    plain = write_spec_json(
        SPEC_TEXT, "requirements.md", tmp_path / "plain.json", FakeProvider()
    )
    marked = write_spec_json(
        SPEC_TEXT,
        "requirements.md",
        tmp_path / "marked.json",
        FakeProvider(),
        progress=events.append,
    )

    assert plain.read_bytes() == marked.read_bytes()
    assert events