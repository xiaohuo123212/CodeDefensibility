"""三态判定与追问/补齐文案（C-MATCHER@2）。

本批永不产出 ``contradicted``：没有充分反证时只下 ``no_evidence``。
三态只由证据决定，``search_trace`` 仅用于 coverage 判定与报告。
feature 类额外要求证据与需求关键词相关；定位选点一律避开依赖声明。
"""

from __future__ import annotations

from .baseline import is_prevalent
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

_STRENGTH_RANK: dict[Strength, int] = {
    Strength.high: 3,
    Strength.medium: 2,
    Strength.low: 1,
}

_COVERAGE_ARTIFACT_HINTS = (".coverage", "coverage.xml", "coverage.json", "coverage.csv", "htmlcov")


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


def _mentions(evidence: Evidence, terms: tuple[str, ...]) -> bool:
    haystack = f"{evidence.file} {evidence.snippet}".lower()
    return any(term in haystack for term in terms)


def _is_dependency_declaration(evidence: Evidence) -> bool:
    name = evidence.file.replace("\\", "/").rsplit("/", 1)[-1].lower()
    return name in DEPENDENCY_DECLARATIONS or name.startswith("requirements")


def _locator_evidence(items: list[Evidence]) -> Evidence | None:
    # 依赖声明只能证明「装了包」，指出不了功能在哪，因此定位优先避开它们
    non_dependency = [e for e in items if not _is_dependency_declaration(e)]
    best = _strongest(non_dependency)
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
        terms = feature_terms(claim.text)
        if terms:
            relevant = [e for e in relevant if _mentions(e, terms)]
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
    if verdict.status is Status.no_evidence and is_prevalent(claim.type, prevalence):
        return "该补"
    return "行业常态"


def question(claim: Claim, verdict: Verdict) -> str:
    template = QUESTION_TEMPLATES[claim.type]
    return template.format(text=_short(claim.text))


def fix(claim: Claim, verdict: Verdict) -> str:
    if verdict.status is Status.supported:
        return "无需补齐：证据已足够。"
    return FIX_TEMPLATES[claim.type]