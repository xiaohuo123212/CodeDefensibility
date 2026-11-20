"""negation 抽取器：显式否定与未实现声明（C-EXTRACTOR@8）。

只判断"这一行是显式否定"，与某条需求是否相关由 Matcher 判定。
已知语义边界：``仅支持`` 是"支持范围受限"，属于比"不支持"更温和的反证，仍按
``strength=high`` 处理，并保留原文 snippet 供人核。

``TODO`` / ``FIXME`` 行必须同时提到实现相关词才算否定，避免无意义 TODO 泛滥。

@8 的边界：否定词只有落在"功能缺失"语境才算反证。标识符（``_lifetime_unsupported_reason``）、
降级路径（``falling back to SoftFileLock``）、测试期望（``pytest.raises(match=...)``）、
待抛消息赋值（``msg = "... is not supported ..."``）四类语境一律不算。
"""

from __future__ import annotations

import re

from ..index import RepoIndex
from ..schema import ClaimType, Evidence, EvidenceKind, Strength
from . import SOURCE_LIMIT, _clip

NEGATION_MARKERS: tuple[str, ...] = (
    "不支持",
    "暂不支持",
    "尚未支持",
    "未实现",
    "暂未实现",
    "尚未实现",
    "待实现",
    "not supported",
    "unsupported",
    "not implemented",
    "only supports",
    "仅支持",
)

TODO_MARKERS = ("todo", "fixme")
TODO_CONTEXT = ("实现", "implement", "support")
SUFFIXES = frozenset(
    {
        ".py",
        ".js",
        ".ts",
        ".tsx",
        ".jsx",
        ".java",
        ".go",
        ".rb",
        ".sh",
        ".md",
        ".txt",
        ".toml",
        ".cfg",
        ".ini",
        ".yaml",
        ".yml",
    }
)
CAP = 40
SUPPORTS = [ClaimType.performance, ClaimType.concurrency, ClaimType.feature, ClaimType.testing]

# 参数校验型异常：其消息里的否定词描述的是入参不合法，不是功能未实现。
_EXCEPTION_GUARD = (
    "valueerror(",
    "typeerror(",
    "keyerror(",
    "attributeerror(",
    "assertionerror(",
    "indexerror(",
    "oserror(",
    "lookuperror(",
    "overflowerror(",
)

# 降级/回退说明：描述的是运行时降级路径，不是功能缺失（C-EXTRACTOR@8）。
_FALLBACK_WORDS = ("falling back", "fallback", "回退", "降级", "退化")

# 测试断言：断言里出现的否定文本是对异常消息的期望，不是代码声明（C-EXTRACTOR@8）。
_TEST_GUARD = ("pytest.raises", "assertraises", "assertwarns", "assert_raises")

# 待抛出的错误消息：消息内容描述入参不合法或组合受限，不是功能未实现（C-EXTRACTOR@8）。
_MESSAGE_ASSIGN_RE = re.compile(r"^(msg|message|reason|detail|err_msg|errmsg)\s*=\s*[frbu]?['\"]")

# 控制流表达式里的取反（``if preserve and not supported:``）不是自然语言否定（C-EXTRACTOR@8）。
_CONTROL_FLOW = ("if ", "elif ", "while ", " and ", " or ", "return ", "assert ")

# 注释里的英文技术短语（如 errno 名 ``"operation not supported"``）不算功能声明（C-EXTRACTOR@8）。
_COMMENT_PREFIXES = ("#", "//", "/*", "*")


def _in_comment(lowered: str, index: int) -> bool:
    """marker 是否落在注释区：行首即是注释，或位于行内 ``#`` 之后。"""
    if lowered.lstrip().startswith(_COMMENT_PREFIXES):
        return True
    hash_at = lowered.find("#")
    return 0 <= hash_at < index


def _is_control_flow_expression(lowered: str, index: int) -> bool:
    """marker 处在代码表达式的取反位置时，视为变量取反而非功能缺失（C-EXTRACTOR@8）。

    只对**代码区**的纯 ASCII 行生效：注释里的自然语言否定（``# if 需要就 return，暂不支持并发``）
    、行尾注释里的英文否定（``x = 1  # ... not implemented``）都仍判为反证。
    """
    if _inside_string_literal(lowered, index):
        return False
    if _in_comment(lowered, index):
        return False
    if any("\u4e00" <= ch <= "\u9fff" for ch in lowered):
        return False
    return any(token in lowered for token in _CONTROL_FLOW)


def _is_english_quoted_in_comment(lowered: str, index: int) -> bool:
    """注释行里引号包裹的纯英文短语不算功能声明（C-EXTRACTOR@8）。

    ``# ... cannot name "operation not supported" ...`` 讲的是 errno 语义；中文注释里的
    「暂不支持」不在引号内，仍判为反证。
    """
    if not _in_comment(lowered, index):
        return False
    if any("\u4e00" <= ch <= "\u9fff" for ch in lowered):
        return False
    return _inside_string_literal(lowered, index)


def _is_identifier_marker(lowered: str, index: int, marker: str) -> bool:
    """marker 处在标识符或变量名位置时不算自然语言否定（C-EXTRACTOR@8）。

    ``_lifetime_unsupported_reason`` / ``_HARD_LINK_UNSUPPORTED_ERRNOS`` 这类标识符里的
    ``unsupported`` 不是对功能的声明；``unsupported = (...)` 的变量赋值同理。中文 marker
    不参与本判定。
    """
    if not marker.isascii():
        return False
    before = lowered[index - 1] if index else ""
    after_at = index + len(marker)
    after = lowered[after_at] if after_at < len(lowered) else ""
    if before and (before.isalnum() or before == "_"):
        return True
    if after and (after.isalnum() or after == "_"):
        return True
    return lowered[after_at:].lstrip().startswith("=")


def _is_test_expectation(lowered: str, index: int) -> bool:
    """测试断言中字符串字面量内的否定词不算反证（C-EXTRACTOR@8）。"""
    if not any(token in lowered for token in _TEST_GUARD):
        return False
    return _inside_string_literal(lowered, index)


def _inside_string_literal(text: str, index: int) -> bool:
    prefix = text[:index]
    return prefix.count('"') % 2 == 1 or prefix.count("'") % 2 == 1


def _is_negation_line(text: str) -> bool:
    lowered = text.lower()
    guarded = any(token in lowered for token in _EXCEPTION_GUARD) or bool(
        _MESSAGE_ASSIGN_RE.match(lowered)
    )
    fallback = any(word in lowered for word in _FALLBACK_WORDS)
    for marker in NEGATION_MARKERS:
        index = lowered.find(marker)
        if index < 0:
            continue
        if fallback:
            continue
        if _is_identifier_marker(lowered, index, marker):
            continue
        if _is_control_flow_expression(lowered, index):
            continue
        if _is_english_quoted_in_comment(lowered, index):
            continue
        if _is_test_expectation(lowered, index):
            continue
        if guarded and _inside_string_literal(lowered, index):
            continue
        return True
    return any(token in lowered for token in TODO_MARKERS) and any(
        word in lowered for word in TODO_CONTEXT
    )


def extract(index: RepoIndex) -> list[Evidence]:
    out: list[Evidence] = []
    seen: set[tuple[str, int | None]] = set()

    for p in index.files:
        if p.suffix.lower() not in SUFFIXES:
            continue
        rel = index.rel(p)
        for raw in index.read(p, limit=SOURCE_LIMIT).splitlines():
            snippet = raw.strip()
            if not snippet or not _is_negation_line(snippet):
                continue
            line = index.line_of(p, snippet)
            key = (rel, line)
            if key in seen:
                continue
            seen.add(key)
            if len(out) >= CAP:
                return out
            out.append(
                Evidence(
                    id=f"ev-negation-{len(out) + 1:03d}",
                    kind=EvidenceKind.code,
                    file=rel,
                    line=line,
                    snippet=_clip(snippet),
                    supports=list(SUPPORTS),
                    strength=Strength.high,
                )
            )

    return out