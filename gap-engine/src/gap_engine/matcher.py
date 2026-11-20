"""三态判定与追问/补齐文案（C-MATCHER@2 / C-MATCHER@4）。

``contradicted`` 只在「有显式否定声明、与需求关键词相关、且有可用行号」时产出；
其余情况仍只下 ``no_evidence``。三态只由证据决定，``search_trace`` 仅用于 coverage 判定与报告。
feature 类额外要求证据与需求关键词相关；定位选点一律避开依赖声明。
"""

from __future__ import annotations

import re

from .baseline import is_prevalent
from .extractors.negation import NEGATION_MARKERS
from .schema import (
    Claim,
    ClaimType,
    Confidence,
    Coverage,
    Evidence,
    EvidenceKind,
    Locator,
    SearchProbe,
    Status,
    Strength,
    Verdict,
)

LOCAL_COMPLETION_PROMPT = """如果代码是下面这样，这句话应该怎么写？

【仓库代码】
{code}

【README 原句】
{text}

请按"代码实际能做到什么"改写这句话：只描述代码里真实存在的入口、配置与测量结果；
代码里没有的部分不要补进句子里。"""

FEATURE_TERM_GROUPS: tuple[tuple[str, ...], ...] = (
    ("导出", "export"),
    ("导入", "import"),
    ("登录", "login", "auth"),
    ("注册", "register", "signup"),
    ("搜索", "search"),
    ("上传", "upload"),
    ("下载", "download"),
    ("支付", "pay"),
    ("通知", "notify", "notification"),
    ("权限", "permission", "role"),
    ("统计", "statistics", "stat"),
    ("报表", "report"),
    ("可视化", "visual", "chart"),
    ("图表", "chart"),
    ("缓存", "cache"),
    ("队列", "queue"),
    ("定时", "cron", "schedule"),
    ("excel", "xlsx", "openpyxl", "workbook"),
)

IMPL_TERM_GROUPS: tuple[tuple[str, ...], ...] = (
    ("协程", "coroutine"),
    ("异步", "async", "await"),
    ("同步 with", "sync", "synchronous"),
    ("订阅者", "subscriber", "receiver", "subscribe"),
    ("信号", "signal", "emit"),
    ("分隔符", "sep", "separator"),
    ("压缩", "compress", "zlib", "deflate"),
    ("时间戳", "timestamp", "max_age"),
    ("序列化", "serializer", "serialize", "dumps", "loads"),
    ("单例", "singleton"),
    ("重入", "reentrant", "reentry", "recursion"),
    ("回调", "callback", "on_acquired"),
    ("弱引用", "weakref", "weak"),
    ("截断", "truncate", "truncated"),
    ("过期", "expire", "expiry", "lifetime", "max_age"),
    ("文件描述符", "descriptor", "fileno"),
    ("心跳", "heartbeat"),
    ("死锁", "deadlock"),
    ("写者", "writer"),
    ("平台", "platform"),
    ("进程间", "interprocess"),
)

DEPENDENCY_DECLARATIONS: tuple[str, ...] = (
    "requirements.txt",
    "requirements-dev.txt",
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "package.json",
    "poetry.lock",
    "pipfile",
    "go.mod",
    "cargo.toml",
    "pom.xml",
)

_ABILITY_TYPES = (ClaimType.performance, ClaimType.concurrency)

CLAIM_STOPWORDS: tuple[str, ...] = (
    "支持",
    "需要",
    "必须",
    "应该",
    "能够",
    "可以",
    "实现",
    "功能",
    "系统",
    "用户",
    "我们",
    "以及",
    "并且",
    "同时",
    "保证",
    "提供",
    "一个",
    "进行",
)

_WORD_RE = re.compile(r"[a-z0-9_]+")
_CJK_RE = re.compile(r"[\u4e00-\u9fff]+")
_STOPWORD_RE = re.compile("|".join(CLAIM_STOPWORDS))

_STRENGTH_RANK: dict[Strength, int] = {
    Strength.high: 3,
    Strength.medium: 2,
    Strength.low: 1,
}

_COVERAGE_ARTIFACT_HINTS = (".coverage", "coverage.xml", "coverage.json", "coverage.csv", "htmlcov")


CONTRADICTED_QUESTION_TEMPLATE = "「{text}」的要求与代码里的否定声明冲突，最终以哪边为准？"
CONTRADICTED_FIX = (
    "代码与要求不一致：先确认这条要求是否仍然有效；"
    "有效就改实现，无效就改需求文档，不要两边都留着。"
)


QUESTION_TEMPLATES: dict[ClaimType, str] = {
    ClaimType.performance: "「{text}」对应的压测脚本与压测结果（并发数、延迟分位数、吞吐）在哪里？",
    ClaimType.concurrency: "「{text}」是在哪份压测脚本和哪种进程/线程配置下测得的？结果文件在哪里？",
    ClaimType.testing: "「{text}」的覆盖率报告（coverage.xml 或 htmlcov）在哪次提交上生成？",
    ClaimType.feature: "「{text}」对应的入口/路由与实现文件分别在哪里？能否给出一条可复现的调用？",
    ClaimType.architecture: "「{text}」的模块边界与数据流画在哪份文档里？各模块分别对应哪些文件？",
    ClaimType.scale: "「{text}」的容量上限是怎么得出的？请给出数据量与验证方式。",
    ClaimType.security: "「{text}」的安全措施实现在哪个文件？有无对应测试或扫描报告？",
}

FIX_TEMPLATES: dict[ClaimType, str] = {
    ClaimType.performance: "补一个可复跑的压测脚本（如 locustfile.py）并把结果文件提交到仓库。",
    ClaimType.concurrency: "补一个并发压测脚本与结果文件，并说明 worker/线程配置与并发数的对应关系。",
    ClaimType.testing: "跑一次覆盖率并把报告（coverage.xml 或 htmlcov/）提交到仓库。",
    ClaimType.feature: "在 README 里给出该功能的入口定义与实现文件相对路径。",
    ClaimType.architecture: "补一份模块划分说明，逐条对应到文件路径。",
    ClaimType.scale: "补一条容量验证记录：数据量、耗时与机器规格。",
    ClaimType.security: "补上安全措施的实现文件位置与一次验证记录。",
}


def _kind(evidence: Evidence) -> EvidenceKind | None:
    try:
        return EvidenceKind(evidence.kind)
    except ValueError:
        return None


def _strongest(items: list[Evidence]) -> Evidence | None:
    best: Evidence | None = None
    best_rank = 0
    for item in items:
        rank = _STRENGTH_RANK.get(item.strength, 0)
        if rank > best_rank:
            best, best_rank = item, rank
    return best


def _locator(evidence: Evidence | None) -> Locator | None:
    if evidence is None:
        return None
    return Locator(file=evidence.file, line=evidence.line, snippet=evidence.snippet or None)


def feature_terms(text: str) -> tuple[str, ...]:
    low = text.lower()
    terms: list[str] = []
    for group in FEATURE_TERM_GROUPS:
        if any(word in low for word in group):
            terms.extend(word for word in group if word not in terms)
    return tuple(terms)


def impl_terms(text: str) -> tuple[str, ...]:
    """从需求文本提取对应的英文实现词（C-MATCHER@7）。

    与 ``feature_terms`` 同构，但英文词的**触发**判定走 C-MATCHER@6 的 ASCII 词边界：
    ``AsyncFileLock`` 里的 ``sync`` 是连写标识符的一部分，不应把 ``sync`` 并进来。
    """
    low = text.lower()
    terms: list[str] = []
    for group in IMPL_TERM_GROUPS:
        if any(_group_word_hit(low, word) for word in group):
            terms.extend(word for word in group if word not in terms)
    return tuple(terms)


def _group_word_hit(low: str, word: str) -> bool:
    if word.isascii():
        return _latin_pattern(word).search(low) is not None
    return word in low


def claim_terms(text: str) -> tuple[str, ...]:
    """从需求文本提取显著词：英文词取 ≥3 字符，中文按停用词切分后取 2–6 字片段。"""
    terms: list[str] = []

    for word in _WORD_RE.findall(text.lower()):
        if len(word) >= 3 and word not in terms:
            terms.append(word)

    for chunk in _CJK_RE.findall(text):
        for piece in _STOPWORD_RE.split(chunk):
            if len(piece) > 6:
                piece = piece[:6]
            if len(piece) >= 2 and piece not in terms:
                terms.append(piece)

    return tuple(terms)


_LATIN_TERM_RE: dict[str, re.Pattern[str]] = {}


def _latin_pattern(term: str) -> re.Pattern[str]:
    # 下划线视为分词符：``_export_rows`` 里的 export 是独立词元，
    # 而 ``getlevelnamesmapping`` 里的 eln 只是字母连写，不算命中。
    pattern = _LATIN_TERM_RE.get(term)
    if pattern is None:
        pattern = re.compile(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])")
        _LATIN_TERM_RE[term] = pattern
    return pattern


def _name_and_snippet(evidence: Evidence) -> str:
    """证据的**文件名**与代码片段（不含目录，C-MATCHER@9）。"""
    name = evidence.file.replace("\\", "/").rsplit("/", 1)[-1]
    return f"{name} {evidence.snippet}".lower()


def mentions(evidence: Evidence, terms: tuple[str, ...]) -> bool:
    """证据是否提到任一关键词（C-MATCHER@6）。

    纯 ASCII 词按**词边界**匹配：需求里的 ``.eln`` 会切出 ``eln``，裸子串会命中
    ``channel`` / ``internal`` 这类无关标识符；边界匹配后只有真正的独立词
    （``foo.eln`` 的 ``eln``、``target``）才算命中。中文仍按子串匹配——
    中文没有词边界概念，且子串匹配是既有判定依赖的语义。

    路径只取文件名（C-MATCHER@9）：目录名里的包名（``src/filelock/``）会让仓库
    里每个文件都恒命中需求中的库名，只有文件名能表达「这个文件是什么」。
    """
    haystack = _name_and_snippet(evidence)
    for term in terms:
        if term.isascii():
            if _latin_pattern(term.lower()).search(haystack):
                return True
        elif term in haystack:
            return True
    return False


_GENERIC_TERMS = frozenset({"true", "false", "none", "null"})


def _mentions_snippet(evidence: Evidence, terms: tuple[str, ...]) -> bool:
    """反证相关性只看声明本身（C-MATCHER@8）。

    文件路径只能定位、不能表达语义：需求里出现包名时，``src/<pkg>/`` 下的每个
    否定行都会因路径命中而被当成相关声明；``True`` / ``None`` 这类字面量关键
    词同样没有区分度，一并排除。
    """
    haystack = (evidence.snippet or "").lower()
    for term in terms:
        if term.isascii():
            if _latin_pattern(term.lower()).search(haystack):
                return True
        elif term in haystack:
            return True
    return False


def _is_negation(evidence: Evidence) -> bool:
    haystack = (evidence.snippet or "").lower()
    return any(marker in haystack for marker in NEGATION_MARKERS)


def _is_dependency_declaration(evidence: Evidence) -> bool:
    name = evidence.file.replace("\\", "/").rsplit("/", 1)[-1].lower()
    return name in DEPENDENCY_DECLARATIONS or name.startswith("requirements")


def _locator_evidence(items: list[Evidence]) -> Evidence | None:
    # 依赖声明只能证明「装了包」，指出不了功能在哪，因此定位优先避开它们；
    # 同理，非反证结论的定位不应落在一条否定声明上（C-MATCHER@8）
    candidates = [e for e in items if not _is_dependency_declaration(e)]
    non_negation = [e for e in candidates if not _is_negation(e)]
    best = _strongest(non_negation)
    if best is not None:
        return best
    best = _strongest(candidates)
    return best if best is not None else _strongest(items)


def _coverage(trace: list[SearchProbe]) -> Coverage:
    if not trace:
        return Coverage.none
    if sum(probe.scanned for probe in trace) == 0:
        return Coverage.none
    if any(probe.hits for probe in trace):
        return Coverage.full
    return Coverage.partial


def _has_coverage_artifact(relevant: list[Evidence]) -> bool:
    for evidence in relevant:
        name = evidence.file.lower().replace("\\", "/")
        if any(hint in name for hint in _COVERAGE_ARTIFACT_HINTS):
            return True
    return False


def _short(text: str, limit: int = 40) -> str:
    flat = " ".join(text.split())
    return flat if len(flat) <= limit else flat[: limit - 1] + "…"


def _verdict(
    claim: Claim,
    status: Status,
    confidence: Confidence,
    locator: Locator | None,
    coverage: Coverage,
    relevant: list[Evidence],
    reason: str,
    trace: list[SearchProbe],
    rounds: int,
) -> Verdict:
    return Verdict(
        claim_id=claim.id,
        status=status,
        confidence=confidence,
        locator=locator,
        coverage=coverage,
        evidence_ids=[e.id for e in relevant],
        reason=reason,
        search_trace=list(trace),
        rounds=rounds,
    )


def judge(
    claim: Claim,
    evidence: list[Evidence],
    trace: list[SearchProbe],
    l: Locator | None = None,
    *,
    rounds: int = 1,
) -> Verdict:
    known = [e for e in evidence if _kind(e) is not None]
    relevant = [e for e in known if claim.type in e.supports]
    scanned_total = sum(probe.scanned for probe in trace)

    if not relevant:
        return _verdict(
            claim,
            Status.no_evidence,
            Confidence.low,
            l,
            Coverage.none if scanned_total == 0 else Coverage.partial,
            [],
            "未找到相关证据",
            trace,
            rounds,
        )

    terms = claim_terms(claim.text)
    if terms:
        # 反证相关性额外并入中英实现词（C-MATCHER@7），只作用于本处判定
        negation_terms = tuple(
            t
            for t in terms + tuple(x for x in impl_terms(claim.text) if x not in terms)
            if t not in _GENERIC_TERMS
        )
        negations = [e for e in relevant if _is_negation(e) and _mentions_snippet(e, negation_terms)]
        anchor = _strongest([e for e in negations if e.line is not None])
        if anchor is not None:
            supports = [e for e in relevant if not _is_negation(e)]
            reason = f"代码里有反证：{_short(anchor.snippet)}"
            if supports:
                reason += f"（另有 {len(supports)} 处支持痕迹，被反证推翻）"
            return _verdict(
                claim,
                Status.contradicted,
                Confidence.high,
                _locator(anchor),
                _coverage(trace),
                relevant,
                reason,
                trace,
                rounds,
            )

    if claim.type in _ABILITY_TYPES:
        bench = [e for e in relevant if _kind(e) is EvidenceKind.bench]
        if not bench:
            return _verdict(
                claim,
                Status.no_evidence,
                Confidence.medium,
                _locator(_locator_evidence(relevant)),
                Coverage.partial,
                relevant,
                "有配置，无测量",
                trace,
                rounds,
            )
        return _verdict(
            claim,
            Status.supported,
            Confidence.high,
            _locator(_locator_evidence(bench)),
            _coverage(trace),
            relevant,
            "找到压测证据",
            trace,
            rounds,
        )

    if claim.type is ClaimType.feature:
        # feature_terms 非空时不得混入 claim_terms，否则已正确的判定会漂移
        terms = feature_terms(claim.text) or claim_terms(claim.text)
        if not terms:
            return _verdict(
                claim,
                Status.no_evidence,
                Confidence.low,
                None,
                _coverage(trace),
                [],
                "需求文本无可用于匹配的关键词",
                trace,
                rounds,
            )
        relevant = [e for e in relevant if mentions(e, terms)]
        if not relevant:
            return _verdict(
                claim,
                Status.no_evidence,
                Confidence.low,
                None,
                _coverage(trace),
                [],
                "未找到与该功能关键词相关的实现",
                trace,
                rounds,
            )

    if claim.type is ClaimType.testing and not _has_coverage_artifact(relevant):
        return _verdict(
            claim,
            Status.no_evidence,
            Confidence.medium,
            _locator(_locator_evidence(relevant)),
            Coverage.partial,
            relevant,
            "有测试，无覆盖结论",
            trace,
            rounds,
        )

    confidence = (
        Confidence.high
        if any(e.strength is Strength.high for e in relevant)
        else Confidence.medium
    )
    return _verdict(
        claim,
        Status.supported,
        confidence,
        _locator(_locator_evidence(relevant)),
        _coverage(trace),
        relevant,
        "找到支持证据",
        trace,
        rounds,
    )


def gap_label(
    claim: Claim,
    verdict: Verdict,
    prevalence: dict[ClaimType, float] | None = None,
) -> str:
    if verdict.status is Status.supported:
        return ""
    if verdict.status is Status.contradicted:
        return "该改"
    if verdict.status is Status.no_evidence and is_prevalent(claim.type, prevalence):
        return "该补"
    return "行业常态"


def question(claim: Claim, verdict: Verdict) -> str:
    if verdict.status is Status.contradicted:
        return CONTRADICTED_QUESTION_TEMPLATE.format(text=_short(claim.text))
    template = QUESTION_TEMPLATES[claim.type]
    return template.format(text=_short(claim.text))


def fix(claim: Claim, verdict: Verdict) -> str:
    if verdict.status is Status.supported:
        return "无需补齐：证据已足够。"
    if verdict.status is Status.contradicted:
        return CONTRADICTED_FIX
    return FIX_TEMPLATES[claim.type]