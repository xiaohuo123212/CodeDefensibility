"""需求清单固化：把规则解析结果落盘为 ``gap-spec@1`` JSON（C-LLM@1/specjson@2）。

``items`` 的 ``text`` / ``line`` / ``decidable`` 唯一来源是 ``spec.parse_spec``；
``provider`` 非空时，模型只被用来把**不可判定条目**改写成一条可验收判据写进
``suggestion``，并随 JSON 一起落盘固化——后续对账只读该文件、不再重算判据。

运行时不以 ``llm`` 模块存在为前提：``LlmProvider`` 仅在类型检查期引用，
有 provider 时优先借用 ``llm.as_llm_fn`` 的吞异常语义，取不到就本地等价实现。
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .progress import LABEL_CRITERIA, PHASE_DONE, PHASE_START, ProgressEvent, ProgressFn
from .spec import SpecItem, parse_spec

if TYPE_CHECKING:
    from .llm import LlmProvider

SPEC_SCHEMA = "gap-spec@1"
PROVIDER_NONE = "none"
CRITERIA_MAX_CHARS = 200
CRITERIA_PROMPT = (
    "把下面这条软件需求改写为一条可验收的量化判据。"
    "只输出判据本身，一行，不超过 40 个汉字，不要解释，不要给文件路径或行号。\n"
    "需求原文：{text}"
)


def build_spec_document(
    text: str,
    spec_path: str,
    provider: LlmProvider | None,
    progress: ProgressFn | None = None,
) -> dict[str, object]:
    items = parse_spec(text)
    llm_fn = _llm_fn_for(provider)
    total = sum(1 for item in items if not item.decidable)
    payload_items: list[dict[str, object]] = []
    called = 0
    for item in items:
        suggestion = item.suggestion
        if llm_fn is not None and not item.decidable:
            called += 1
            criteria = _criteria_for(llm_fn, item.text, progress, called, total)
            if criteria:
                suggestion = criteria
        payload_items.append(_item_to_payload(item, suggestion))
    return {
        "schema": SPEC_SCHEMA,
        "source": spec_path,
        "provider": PROVIDER_NONE if provider is None else provider.name,
        "items": payload_items,
        "dropped": 0,
    }


def write_spec_json(
    text: str,
    spec_path: str,
    out: Path,
    provider: LlmProvider | None,
    progress: ProgressFn | None = None,
) -> Path:
    target = Path(out)
    target.parent.mkdir(parents=True, exist_ok=True)
    document = build_spec_document(text, spec_path, provider, progress)
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
        except Exception:  # 判据是可选增强，失败不得影响落盘
            return ""
        return answer if isinstance(answer, str) else ""

    return call


def _criteria_for(
    llm_fn: Callable[[str], str],
    text: str,
    progress: ProgressFn | None = None,
    index: int = 0,
    total: int = 0,
) -> str:
    """取模型返回值 strip 后的第一个非空行；空串交由调用方保留规则值。

    ``llm_fn`` 自身吞异常，故 ``start`` / ``done`` 必然成对发出。
    """
    _emit(progress, PHASE_START, index, total, text, 0.0)
    started = time.perf_counter()
    answer = llm_fn(CRITERIA_PROMPT.format(text=text))
    _emit(progress, PHASE_DONE, index, total, text, time.perf_counter() - started)
    for line in answer.splitlines():
        candidate = line.strip()
        if candidate:
            return candidate[:CRITERIA_MAX_CHARS]
    return ""


def _emit(
    progress: ProgressFn | None, phase: str, index: int, total: int, text: str, seconds: float
) -> None:
    if progress is None:
        return
    progress(ProgressEvent(phase, index, total, LABEL_CRITERIA, text, seconds))


def _item_to_payload(item: SpecItem, suggestion: str) -> dict[str, object]:
    return {
        "text": item.text,
        "line": item.line,
        "decidable": item.decidable,
        "suggestion": suggestion,
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