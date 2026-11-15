"""需求清单固化：把规则解析结果落盘为 ``gap-spec@1`` JSON（C-LLM@1/specjson）。

``items`` 的唯一来源是 ``spec.parse_spec``；LLM 只参与归类，归类结果不入盘，
因此同一份需求清单两次解析得到逐字节相同的 JSON，后续对账可只读该文件复现条目集合。

运行时不以 ``llm`` 模块存在为前提：``LlmProvider`` 仅在类型检查期引用，
有 provider 时优先借用 ``llm.as_llm_fn`` 的吞异常语义，取不到就本地等价实现。
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .claimer import classify
from .spec import SpecItem, parse_spec

if TYPE_CHECKING:
    from .llm import LlmProvider

SPEC_SCHEMA = "gap-spec@1"
PROVIDER_NONE = "none"


def build_spec_document(
    text: str, spec_path: str, provider: LlmProvider | None
) -> dict[str, object]:
    items = parse_spec(text)
    llm_fn = _llm_fn_for(provider)
    if llm_fn is not None:
        for item in items:
            classify(item.text, llm_fn)
    return {
        "schema": SPEC_SCHEMA,
        "source": spec_path,
        "provider": PROVIDER_NONE if provider is None else provider.name,
        "items": [_item_to_payload(item) for item in items],
        "dropped": 0,
    }


def write_spec_json(
    text: str, spec_path: str, out: Path, provider: LlmProvider | None
) -> Path:
    target = Path(out)
    target.parent.mkdir(parents=True, exist_ok=True)
    document = build_spec_document(text, spec_path, provider)
    payload = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
    # 同目录临时文件 + 替换，避免半个 JSON 覆盖既有产物
    staged = target.with_name(f"{target.name}.tmp")
    staged.write_text(payload, encoding="utf-8", newline="\n")
    os.replace(staged, target)
    return target


def load_spec_json(path: Path) -> list[SpecItem]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("gap-spec JSON 顶层必须是对象")
    schema = data.get("schema")
    if schema != SPEC_SCHEMA:
        raise ValueError(f"schema 必须为 {SPEC_SCHEMA}，实际为 {schema!r}")
    raw_items = data.get("items")
    if not isinstance(raw_items, list):
        raise ValueError("items 必须是数组")
    return [_item_from_payload(raw, index) for index, raw in enumerate(raw_items)]


def _llm_fn_for(provider: LlmProvider | None) -> Callable[[str], str] | None:
    if provider is None:
        return None
    try:
        from .llm import as_llm_fn
    except ImportError:
        return _safely(provider)
    llm_fn = as_llm_fn(provider)
    return llm_fn if llm_fn is not None else _safely(provider)


def _safely(provider: LlmProvider) -> Callable[[str], str]:
    def call(prompt: str) -> str:
        try:
            answer = provider.complete(prompt)
        except Exception:  # 归类是可选增强，失败不得影响落盘
            return ""
        return answer if isinstance(answer, str) else ""

    return call


def _item_to_payload(item: SpecItem) -> dict[str, object]:
    return {
        "text": item.text,
        "line": item.line,
        "decidable": item.decidable,
        "suggestion": item.suggestion,
    }


def _item_from_payload(raw: Any, index: int) -> SpecItem:
    if not isinstance(raw, dict):
        raise ValueError(f"items[{index}] 必须是对象")
    text = raw.get("text")
    line = raw.get("line")
    decidable = raw.get("decidable")
    suggestion = raw.get("suggestion")
    if not isinstance(text, str):
        raise ValueError(f"items[{index}].text 必须是字符串")
    if not isinstance(line, int) or isinstance(line, bool):
        raise ValueError(f"items[{index}].line 必须是整数")
    if not isinstance(decidable, bool):
        raise ValueError(f"items[{index}].decidable 必须是布尔值")
    if not isinstance(suggestion, str):
        raise ValueError(f"items[{index}].suggestion 必须是字符串")
    return SpecItem(text=text, line=line, decidable=decidable, suggestion=suggestion)