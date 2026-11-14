"""端到端管线：仓库 → 声称/需求 → 探测 → 判定 → 报告（C-PIPELINE@1 / @2 / @3 / @4）。"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from pathlib import Path

from . import matcher, prober
from .claimer import LlmFn, claims_from_readme
from .extractors import EXTRACTORS
from .index import RepoIndex, build_index
from .metrics import compute
from .priority import compute_question_priority
from .renderer import render, render_spec
from .schema import Claim, Evidence, Status, Strength, Verdict, is_judgeable
from .spec import SpecItem, claims_from_spec, parse_spec

_ROUTE_RE = re.compile(
    r"@(?:app|router|bp|blueprint)\.(route|get|post|put|patch|delete)\s*\(\s*[\"']([^\"']+)[\"']",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class SpecAnalysis:
    repo: str
    spec_path: str
    items: tuple[SpecItem, ...]
    claims: tuple[Claim, ...]
    verdicts: tuple[Verdict, ...]
    overview: tuple[str, ...]
    metrics: dict[str, object]
    routes: tuple[str, ...] = ()
    summary: str = ""



def _scope(claims: list[Claim]) -> list[Claim]:
    return [
        replace(
            claim,
            out_of_scope=(not is_judgeable(claim.type)) or claim.out_of_scope,
        )
        for claim in claims
    ]


def _merge_evidence(evidence: list[Evidence]) -> list[Evidence]:
    deduped: dict[str, Evidence] = {}
    for item in evidence:
        deduped.setdefault(item.id, item)
    return list(deduped.values())


def _judge_one(claim: Claim, index: RepoIndex, max_rounds: int) -> Verdict:
    cap = max(1, min(3, max_rounds))
    probes, evidence = prober.run(claim, index, 1)
    trace = list(probes)
    verdict = matcher.judge(claim, evidence, trace, rounds=1)

    # 只有没找到证据才换假设：supported 与 contradicted 都在第 1 轮即定论
    if verdict.status is Status.no_evidence:
        available = 1 + len(prober.ALTERNATE_PLANS.get(claim.type, ()))
        for n in range(2, min(cap, available) + 1):
            more_probes, more = prober.run(claim, index, n)
            trace.extend(more_probes)
            evidence = _merge_evidence(evidence + more)
            verdict = matcher.judge(claim, evidence, trace, rounds=n)
            if verdict.status is Status.supported:
                verdict = replace(verdict, reason=f"第 {n} 轮换假设后找到支持证据")
                break

    verdict.question_priority = compute_question_priority(verdict.status, verdict.confidence)
    verdict.question = matcher.question(claim, verdict)
    verdict.fix = matcher.fix(claim, verdict)
    label = matcher.gap_label(claim, verdict)
    if label:
        verdict.reason = f"{verdict.reason}；缺口：{label}"

    return verdict


def _judge_all(claims: list[Claim], index: RepoIndex, max_rounds: int = 3) -> list[Verdict]:
    return [_judge_one(claim, index, max_rounds) for claim in claims]


def _dedup(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _test_file_count(index: RepoIndex) -> int:
    test_files = _dedup([evidence.file for evidence in EXTRACTORS["tests"](index)])
    return sum(
        1
        for name in (Path(path).name for path in test_files)
        if name.startswith("test_") or "_test" in name
    )


def _overview(index: RepoIndex) -> tuple[str, ...]:
    n_files = len(index.files)
    loc = sum(len(index.read(path).splitlines()) for path in index.files)

    entries = _dedup([evidence.file for evidence in EXTRACTORS["entry"](index)])
    deps = _dedup([evidence.snippet.strip() for evidence in EXTRACTORS["deps"](index)])
    n_tests = _test_file_count(index)

    return (
        f"文件 {n_files} 个，代码 {loc} 行",
        f"入口：{', '.join(entries[:3])}" if entries else "入口：未识别到启动入口",
        f"依赖：{', '.join(deps[:5])}" if deps else "依赖：未识别到依赖声明",
        f"测试：{n_tests} 个测试文件" if n_tests else "测试：未找到测试文件",
    )


def _route_of(snippet: str) -> str:
    match = _ROUTE_RE.search(snippet)
    if match is None:
        return ""
    verb, path = match.group(1).lower(), match.group(2)
    method = "GET" if verb == "route" else verb.upper()
    return f"{method} {path}"


def _routes_and_entry(index: RepoIndex) -> tuple[tuple[str, ...], str]:
    hits = sorted(
        (e for e in EXTRACTORS["entry"](index) if e.strength is not Strength.low),
        key=lambda e: (e.file, e.line),
    )
    routes: list[str] = []
    entry_file = ""
    for evidence in hits:
        route = _route_of(evidence.snippet)
        if not route or route in routes:
            continue
        routes.append(route)
        if not entry_file:
            entry_file = Path(evidence.file).name
    return tuple(routes), entry_file


def _structure_entry(index: RepoIndex) -> str:
    for evidence in EXTRACTORS["structure"](index):
        if evidence.file:
            return Path(evidence.file).name
    return "未找到入口文件"


def _facts(index: RepoIndex) -> tuple[tuple[str, ...], str]:
    routes, entry_file = _routes_and_entry(index)
    if not entry_file:
        entry_file = _structure_entry(index)

    deps = _dedup([evidence.snippet.strip() for evidence in EXTRACTORS["deps"](index)])
    dependency = f"依赖 {len(deps)} 个（{', '.join(deps[:2])}）" if deps else "依赖 0 个"
    n_tests = _test_file_count(index)

    head = f"{entry_file} 暴露 {len(routes)} 个路由" if routes else f"{entry_file} 未见路由定义"
    return routes, f"{head}；{dependency}；{n_tests} 个测试文件。"


def analyze_repo(
    repo: Path,
    claims: list[Claim] | None = None,
    max_rounds: int = 3,
    max_claims: int = 5,
    llm: LlmFn | None = None,
) -> tuple[list[Claim], list[Verdict]]:
    index = build_index(Path(repo))

    raw_claims = claims if claims is not None else claims_from_readme(index, max_claims, llm)
    scoped_claims = _scope(raw_claims)
    verdicts = _judge_all(scoped_claims, index, max_rounds)
    return scoped_claims, verdicts


def analyze_spec(
    repo: Path,
    spec_text: str,
    spec_path: str = "spec.md",
    llm: LlmFn | None = None,
    max_rounds: int = 3,
) -> SpecAnalysis:
    repo = Path(repo)
    index = build_index(repo)
    items = tuple(parse_spec(spec_text))
    claims = tuple(_scope(claims_from_spec(items, spec_path)))
    verdicts = tuple(_judge_all(list(claims), index, max_rounds))

    # spec 模式的条目解析是确定性的，LLM 参数仅为与 D1 入口保持同形
    _ = llm
    routes, summary = _facts(index)
    return SpecAnalysis(
        repo=repo.name,
        spec_path=spec_path,
        items=items,
        claims=claims,
        verdicts=verdicts,
        overview=_overview(index),
        metrics=compute(list(claims), list(verdicts)),
        routes=routes,
        summary=summary,
    )


def render_to(
    repo: Path,
    out: Path,
    claims: list[Claim] | None = None,
    verdicts: list[Verdict] | None = None,
) -> Path:
    repo = Path(repo)
    index = build_index(repo)
    if claims is None or verdicts is None:
        analyzed_claims, analyzed_verdicts = analyze_repo(repo)
        claims = analyzed_claims if claims is None else claims
        verdicts = analyzed_verdicts if verdicts is None else verdicts
    routes, summary = _facts(index)
    return render(
        verdicts,
        claims,
        Path(out),
        repo.name,
        summary=summary,
        routes=routes,
    )


def render_spec_to(repo: Path, spec: Path, out: Path) -> Path:
    spec = Path(spec)
    analysis = analyze_spec(
        Path(repo),
        spec.read_text(encoding="utf-8", errors="replace"),
        spec_path=spec.name,
    )
    return render_spec(
        analysis,
        Path(out),
        summary=analysis.summary,
        routes=analysis.routes,
    )