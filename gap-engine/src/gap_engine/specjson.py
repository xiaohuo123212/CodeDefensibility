"""需求清单固化：把规则解析结果落盘为 ``gap-spec@1`` JSON（C-LLM@1/specjson@6）。

``items`` 的 ``text`` / ``line`` / ``decidable`` 唯一来源是 ``spec.parse_spec``；
``provider`` 非空时，模型只被用来把**不可判定条目**改写成一条可验收判据写进
``suggestion``，并随 JSON 一起落盘固化——后续对账只读该文件、不再重算判据。

运行时不以 ``llm`` 模块存在为前提：``LlmProvider`` 仅在类型检查期引用，
有 provider 时优先借用 ``llm.as_llm_fn`` 的吞异常语义，取不到就本地等价实现。
"""

from __future__ import annotations

import json
import os
import re
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
    "只输出判据本身，一行，不超过 40 个汉字，不要解释，不要给文件路径或行号。"
    "判据必须针对需求提到的对象，不要替换成需求没提到的指标。\n"
    "需求原文：{text}"
)

# 判据必须含可量化阈值或 ``file:`` 定位才算可验收；不复用 spec._MEASURABLE_RE，
# 那条正则面向判定域、放过大量无阈值文本（如「支持配置热更新功能」）。
_CRITERIA_CHECK_RE = re.compile(
    r"\d+(?:\.\d+)?\s*(?:%|ms|毫秒|秒|s\b|分钟|小时|天|次|个|条|类|项|并发|用户|qps|tps|rps|倍|层)"
    r"|P9\d|P5\d|file:\S+",
    re.IGNORECASE,
)

# 候选判据以需求原文开头，有两种情形必须分开处理：
#   原文 + 真澄清（「…，配置变更后5秒内生效」）—— 合格改写，要保住；
#   原文 + 凭空阈值（「…，更新频率不低于1次/天」）—— 阈值是附会上去的，要丢掉。
# 二者只差在残量是否还落在需求话题上，所以剥离复述前缀后还要看残量共享哪些词。
# 比对前剔除空白与中英文标点，避免因标点差异漏判。
_RESTATE_STRIP_CHARS = " \t\r\n，。、；：！？,.;:!?/（）()[]【】「」『』\"'“”‘’·…—-"
_RESTATE_STRIP_RE = re.compile("[" + re.escape(_RESTATE_STRIP_CHARS) + "]")

# 这些词只表明句子的语法骨架，不指向需求的判定对象，不能作为「残量仍在话题上」的凭据。
_RESTATE_GENERIC = frozenset(
    {
        "系统", "支持", "功能", "更新", "提供", "具备", "能够", "要求",
        "相关", "使用", "实现", "处理", "进行", "以及", "可以", "需要", "应当",
        "应", "该", "本",
    }
)

# 与需求共享的非通用二字词覆盖率：越高越像复述，越低越可能离题。
_RESTATE_OVERLAP = 0.5
# 需求至少要有这么多核心二字词，才要求判据必须命中其中一个；短需求没有可复用的名词。
_TOPIC_CORE_MIN = 3


def _bigrams(compact: str) -> set[str]:
    return {compact[index : index + 2] for index in range(len(compact) - 1)}


def _strip_restatement(candidate: str, text: str) -> str:
    """剥离候选判据开头对需求原文的复述，返回余下部分。

    不以原文开头时原样返回；开头即整条复述时返回空串。标点与空白不参与比对，
    定位时按非标点字符计数回切，避免标点差异漏判。
    """
    source = _RESTATE_STRIP_RE.sub("", text)
    if not source or not _RESTATE_STRIP_RE.sub("", candidate).startswith(source):
        return candidate
    seen = 0
    for index, char in enumerate(candidate):
        if _RESTATE_STRIP_RE.fullmatch(char):
            continue
        seen += 1
        if seen == len(source):
            return candidate[index + 1 :].strip(_RESTATE_STRIP_CHARS)
    return ""


def _overlap_ratio(candidate: str, text: str) -> float:
    """候选覆盖了多少需求的核心二字词（通用词不计）。"""
    source = _bigrams(_RESTATE_STRIP_RE.sub("", text)) - _RESTATE_GENERIC
    if not source:
        return 0.0
    return len(source & _bigrams(_RESTATE_STRIP_RE.sub("", candidate))) / len(source)


def _core_topics(text: str) -> set[str]:
    """需求的核心二字词：剥掉开头的通用词与全部通用二字词后剩下的部分。

    开头可能叠着多个通用词（「系统应具备高性能」），要反复剥到不再命中为止，
    否则会把「应具备」这类骨架词当成需求的判定对象。
    """
    compact = _RESTATE_STRIP_RE.sub("", text)
    words = sorted(_RESTATE_GENERIC, key=len, reverse=True)
    stripped = True
    while stripped:
        stripped = False
        for word in words:
            if compact.startswith(word):
                compact = compact[len(word) :]
                stripped = True
                break
    return _bigrams(compact) - _RESTATE_GENERIC


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
    """取第一个剥离复述后仍可验收、且没有离题的行；没有则返回空串。

    以需求原文开头的行先剥离复述前缀，再依次过三道检查：

    1. 残量须自含量化阈值或 ``file:`` 定位；
    2. 残量与需求原文的核心二字词覆盖率不得达到 ``_RESTATE_OVERLAP``——换语序、加主语后
       仍与原文高度重合的，仍然是复述（如原文「配置支持热更新」答成「系统支持配置热更新
       功能，5秒内生效」）；
    3. 需求核心词不少于 ``_TOPIC_CORE_MIN`` 时，残量必须命中至少一个——一个都命不中说明
       判据另起炉灶（如「支持灰度发布」答成「系统支持5%流量分发测试」，丢了「灰度」）。

    短需求（如「高性能」）核心词太少，判据必然换说法，因此豁免第 3 条。空串交由调用方
    保留规则兜底判据。``llm_fn`` 自身吞异常，故 ``start`` / ``done`` 必然成对发出。
    """
    _emit(progress, PHASE_START, index, total, text, 0.0)
    started = time.perf_counter()
    answer = llm_fn(CRITERIA_PROMPT.format(text=text))
    _emit(progress, PHASE_DONE, index, total, text, time.perf_counter() - started)
    core = _core_topics(text)
    for line in answer.splitlines():
        candidate = line.strip()
        if not candidate:
            continue
        rest = _strip_restatement(candidate, text)
        if not rest or not _CRITERIA_CHECK_RE.search(rest):
            continue
        overlap = _overlap_ratio(rest, text)
        if overlap >= _RESTATE_OVERLAP:
            continue
        if overlap == 0 and len(core) >= _TOPIC_CORE_MIN:
            continue
        return rest[:CRITERIA_MAX_CHARS]
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