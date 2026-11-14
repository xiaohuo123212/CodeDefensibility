"""从 README 抽取可判定声称并归入七类（C-CLAIMER@1）。

只做规则：命中能力词或量化词的句子成为 ``Claim``；分类只产出七个枚举值。
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterator

from .index import RepoIndex
from .schema import Claim, ClaimType

LlmFn = Callable[[str], str]

CAPABILITY_MARKERS: tuple[str, ...] = (
    "支持",
    "实现",
    "提供",
    "集成",
    "完成",
    "采用",
    "基于",
    "使用",
    "support",
    "supports",
    "implement",
    "implements",
    "provide",
    "provides",
    "integrate",
    "integrates",
    "built with",
)

QUANT_MARKERS: tuple[str, ...] = (
    "并发",
    "QPS",
    "毫秒",
    "ms",
    "响应时间",
    "延迟",
    "吞吐",
    "万级",
    "十万级",
    "覆盖率",
    "测试",
    "压测",
    "分布式",
    "高可用",
    "高并发",
    "集群",
    "缓存",
    "索引",
)

# 优先级自上而下，先命中者胜；前四类与后三类共用同一套词表不影响分类结果。
_CLASSIFIER_KEYWORDS: tuple[tuple[ClaimType, tuple[str, ...]], ...] = (
    (
        ClaimType.concurrency,
        (
            "并发",
            "QPS",
            "吞吐",
            "集群",
            "线程",
            "协程",
            "并行",
            "worker",
            "thread",
            "threaded",
            "concurrent",
            "throughput",
            "async",
        ),
    ),
    (
        ClaimType.performance,
        (
            "性能",
            "延迟",
            "响应时间",
            "毫秒",
            "latency",
            "加速",
            "优化",
            "benchmark",
            "毫秒级",
            "ms",
        ),
    ),
    (
        ClaimType.testing,
        (
            "测试",
            "覆盖率",
            "单元测试",
            "测试用例",
            "coverage",
            "pytest",
            "unittest",
            "tdd",
        ),
    ),
    (
        ClaimType.feature,
        (
            "导出",
            "导入",
            "上传",
            "下载",
            "接口",
            "API",
            "路由",
            "报表",
            "搜索",
            "批量",
            "登录",
            "可视化",
            "定时任务",
        ),
    ),
    (
        ClaimType.architecture,
        (
            "架构",
            "分层",
            "微服务",
            "模块化",
            "解耦",
            "高可用",
            "可扩展",
            "扩展性",
            "插件",
            "单体",
        ),
    ),
    (
        ClaimType.scale,
        (
            "万级",
            "十万级",
            "百万",
            "亿级",
            "数据量",
            "海量",
            "大文件",
            "水平扩展",
            "分布式",
        ),
    ),
    (
        ClaimType.security,
        (
            "安全",
            "加密",
            "鉴权",
            "认证",
            "授权",
            "权限",
            "漏洞",
            "注入",
            "token",
            "https",
            "审计",
        ),
    ),
)

META_PREFIXES: tuple[str, ...] = (
    "因此",
    "所以",
    "这说明",
    "这表明",
    "注释",
    "注意",
    "示例",
    "例如",
    "期望",
    "应当",
    "应该",
    "本报告",
    "该报告",
    "作为",
    "用途",
    "被断言",
    "局限",
    "免责",
    "本项目仅",
)

META_TOKENS: tuple[str, ...] = (
    "no_evidence",
    "supported",
    "contradicted",
    "应当被判",
    "应被判",
    "缺压测证据",
    "回归基线",
    "对账",
)

_CLAIM_MARKERS: tuple[str, ...] = CAPABILITY_MARKERS + QUANT_MARKERS

_ASCII_WORD = re.compile(r"(?<![a-z]){}(?![a-z])")

_PATTERN_CACHE: dict[str, re.Pattern[str]] = {}

_TITLE_PREFIX = re.compile(r"^#{1,6}\s")
_TABLE_ROW = re.compile(r"^\|")
_LIST_PREFIX = re.compile(r"^(?:[-*+]\s+|\d+[.)]\s+|>\s*)")
_INLINE_MARKUP = re.compile(r"\*\*|`")
_SENTENCE_SPLIT = re.compile(r"[。！？；!?;]+|\.\s+")
_NEGATED_PREFIXES = ("没有", "未", "无", "不", "并非")


def _word_pattern(marker: str) -> re.Pattern[str]:
    pattern = _PATTERN_CACHE.get(marker)
    if pattern is None:
        pattern = re.compile(_ASCII_WORD.pattern.format(re.escape(marker)))
        _PATTERN_CACHE[marker] = pattern
    return pattern


def _hit(lowered: str, marker: str) -> bool:
    marker = marker.lower()
    # 短 ASCII 词（ms / qps / api）需要边界，否则会在 items / capability 里误命中。
    if marker.isascii() and marker.isalpha():
        return _word_pattern(marker).search(lowered) is not None
    return marker in lowered


def _clean(part: str) -> str:
    text = _LIST_PREFIX.sub("", part.strip())
    text = _INLINE_MARKUP.sub("", text)
    return text.strip()


def _sentences(text: str) -> Iterator[str]:
    in_fence = False
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("```"):
            in_fence = not in_fence
            continue
        if not line or in_fence or _TITLE_PREFIX.match(line) or _TABLE_ROW.match(line):
            continue
        for part in _SENTENCE_SPLIT.split(_LIST_PREFIX.sub("", line)):
            sentence = _clean(part)
            if sentence:
                yield sentence


def is_meta_sentence(text: str) -> bool:
    cleaned = _clean(text)
    if cleaned.startswith(META_PREFIXES):
        return True
    lowered = cleaned.lower()
    if any(token.lower() in lowered for token in META_TOKENS):
        return True
    return len(cleaned) < 8


def _is_claimable(sentence: str) -> bool:
    if sentence.startswith(_NEGATED_PREFIXES):
        return False
    lowered = sentence.lower()
    return any(_hit(lowered, marker) for marker in _CLAIM_MARKERS)


def classify(text: str, llm: LlmFn | None = None) -> ClaimType:
    lowered = text.lower()
    for claim_type, keywords in _CLASSIFIER_KEYWORDS:
        if any(_hit(lowered, keyword) for keyword in keywords):
            return claim_type
    if llm is not None:
        try:
            answer = llm(text)
        except Exception:  # LLM 是可选的增强项，失败不得影响规则链路
            answer = ""
        if isinstance(answer, str):
            candidate = answer.strip().lower()
            for claim_type in ClaimType:
                if candidate == claim_type.value:
                    return claim_type
    return ClaimType.feature


def claims_from_text(
    text: str,
    source: str,
    max_claims: int = 5,
    llm: LlmFn | None = None,
) -> list[Claim]:
    if max_claims <= 0:
        return []
    claims: list[Claim] = []
    seen: set[str] = set()
    for sentence in _sentences(text):
        if not _is_claimable(sentence):
            continue
        if is_meta_sentence(sentence):
            continue
        key = sentence.casefold()
        if key in seen:
            continue
        seen.add(key)
        claims.append(
            Claim(
                id=f"c{len(claims) + 1:02d}",
                text=sentence,
                source=source,
                type=classify(sentence, llm),
            )
        )
        if len(claims) >= max_claims:
            break
    return claims


def claims_from_readme(
    index: RepoIndex,
    max_claims: int = 5,
    llm: LlmFn | None = None,
) -> list[Claim]:
    if max_claims <= 0:
        return []
    blocks: list[str] = []
    for path in index.files:
        name = path.name.lower()
        if not (name.startswith("readme") and name.endswith(".md")):
            continue
        content = index.read(path)
        if content:
            blocks.append(content)
    if not blocks:
        return []
    return claims_from_text("\n".join(blocks), "readme", max_claims, llm)