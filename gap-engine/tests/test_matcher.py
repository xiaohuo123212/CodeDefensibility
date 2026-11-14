"""三态判定、缺口标签与追问/补齐文案的单元测试（C-MATCHER@2）。"""

from __future__ import annotations

from pathlib import Path

import gap_engine.matcher as matcher_module
from gap_engine.matcher import (
    FIX_TEMPLATES,
    LOCAL_COMPLETION_PROMPT,
    QUESTION_TEMPLATES,
    FEATURE_TERM_GROUPS,
    _is_dependency_declaration,
    _locator_evidence,
    feature_terms,
    fix,
    gap_label,
    judge,
    question,
)
from gap_engine.schema import (
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


def _claim(ctype: ClaimType, text: str = "支持某能力") -> Claim:
    return Claim(id="c01", text=text, source="readme", type=ctype)


def _evidence(
    kind: EvidenceKind,
    supports: list[ClaimType],
    strength: Strength,
    path: str = "app.py",
    line: int = 1,
) -> Evidence:
    return Evidence(
        id=f"ev-{kind.value}-{line:03d}",
        kind=kind,
        file=path,
        line=line,
        snippet="x" * 10,
        supports=supports,
        strength=strength,
    )


def _probe(hits: int = 1, scanned: int = 3, name: str = "探查") -> SearchProbe:
    return SearchProbe(probe=name, target="target", scanned=scanned, hits=hits, where=[])


def _trace() -> list[SearchProbe]:
    return [_probe(hits=0, scanned=0), _probe(hits=1, scanned=2)]


def test_no_evidence_when_no_relevant_evidence() -> None:
    verdict = judge(_claim(ClaimType.feature), [], _trace())
    assert verdict.status is Status.no_evidence
    assert verdict.confidence is Confidence.low
    assert verdict.coverage is Coverage.partial
    assert verdict.reason.startswith("未找到相关证据")
    assert verdict.locator is None


def test_coverage_none_when_nothing_scanned() -> None:
    verdict = judge(_claim(ClaimType.feature), [], [_probe(scanned=0, hits=0)])
    assert verdict.coverage is Coverage.none


def test_ability_without_bench_is_no_evidence() -> None:
    evidence = [
        _evidence(EvidenceKind.config, [ClaimType.concurrency], Strength.medium, "g.conf", 3),
        _evidence(EvidenceKind.code, [ClaimType.concurrency], Strength.high, "app.py", 7),
    ]
    verdict = judge(_claim(ClaimType.concurrency), evidence, _trace())
    assert verdict.status is Status.no_evidence
    assert verdict.confidence is Confidence.medium
    assert verdict.coverage is Coverage.partial
    assert "有配置，无测量" in verdict.reason
    assert verdict.locator is not None
    assert verdict.locator.file == "app.py"


def test_ability_with_bench_is_supported() -> None:
    evidence = [
        _evidence(EvidenceKind.config, [ClaimType.performance], Strength.medium, "g.conf", 3),
        _evidence(EvidenceKind.bench, [ClaimType.performance], Strength.high, "locustfile.py", 12),
    ]
    verdict = judge(_claim(ClaimType.performance), evidence, _trace())
    assert verdict.status is Status.supported
    assert verdict.confidence is Confidence.high
    assert verdict.locator is not None
    assert (verdict.locator.file, verdict.locator.line) == ("locustfile.py", 12)


def test_testing_with_only_declarations_is_no_evidence() -> None:
    evidence = [_evidence(EvidenceKind.test, [ClaimType.testing], Strength.high, "tests/test_a.py")]
    verdict = judge(_claim(ClaimType.testing), evidence, _trace())
    assert verdict.status is Status.no_evidence
    assert "有测试，无覆盖结论" in verdict.reason
    assert verdict.coverage is Coverage.partial


def test_testing_with_coverage_artifact_is_supported() -> None:
    evidence = [
        _evidence(EvidenceKind.test, [ClaimType.testing], Strength.high, "tests/test_a.py"),
        _evidence(EvidenceKind.test, [ClaimType.testing], Strength.high, "coverage.xml", 1),
    ]
    verdict = judge(_claim(ClaimType.testing), evidence, _trace())
    assert verdict.status is Status.supported
    assert verdict.confidence is Confidence.high


def test_feature_claim_with_evidence_is_supported() -> None:
    evidence = [_evidence(EvidenceKind.code, [ClaimType.feature], Strength.low, "app.py", 5)]
    verdict = judge(_claim(ClaimType.feature), evidence, _trace())
    assert verdict.status is Status.supported
    assert verdict.confidence is Confidence.medium

    evidence.append(_evidence(EvidenceKind.dep, [ClaimType.feature], Strength.medium, "req.txt", 2))
    assert judge(_claim(ClaimType.feature), evidence, _trace()).confidence is Confidence.medium
    assert verdict.search_trace == _trace()
    assert verdict.rounds == 1


def test_judge_never_returns_contradicted() -> None:
    cases = [
        judge(_claim(ClaimType.feature), [], _trace()),
        judge(
            _claim(ClaimType.concurrency),
            [_evidence(EvidenceKind.config, [ClaimType.concurrency], Strength.medium)],
            _trace(),
        ),
        judge(
            _claim(ClaimType.testing),
            [_evidence(EvidenceKind.test, [ClaimType.testing], Strength.high, "test_a.py")],
            _trace(),
        ),
    ]
    assert all(verdict.status is not Status.contradicted for verdict in cases)


def test_unknown_evidence_kind_is_ignored() -> None:
    broken = Evidence(
        id="ev-x",
        kind="mystery",  # type: ignore[arg-type]
        file="app.py",
        line=1,
        snippet="x",
        supports=[ClaimType.feature],
        strength=Strength.high,
    )
    verdict = judge(_claim(ClaimType.feature), [broken], _trace())
    assert verdict.status is Status.no_evidence


def test_local_completion_prompt_shape() -> None:
    assert LOCAL_COMPLETION_PROMPT.startswith("如果代码是下面这样，这句话应该怎么写？")
    for banned in ("是否一致", "是否匹配"):
        assert banned not in LOCAL_COMPLETION_PROMPT


def test_gap_label_double_condition() -> None:
    claim = _claim(ClaimType.performance)
    supported = Verdict(
        claim_id="c01",
        status=Status.supported,
        confidence=Confidence.high,
        locator=Locator("app.py", 1),
        coverage=Coverage.full,
        evidence_ids=[],
        reason="",
        search_trace=_trace(),
    )
    assert gap_label(claim, supported) == ""

    absent = judge(claim, [], _trace())
    assert gap_label(claim, absent) == "行业常态"  # performance 先验 0.30 < 0.5
    assert gap_label(_claim(ClaimType.testing), judge(_claim(ClaimType.testing), [], _trace())) == "该补"
    assert (
        gap_label(
            _claim(ClaimType.performance), absent, {ClaimType.performance: 0.9}
        )
        == "该补"
    )


def test_question_and_fix_templates_cover_all_types() -> None:
    for ctype in ClaimType:
        assert ctype in QUESTION_TEMPLATES
        assert ctype in FIX_TEMPLATES
        verdict = judge(_claim(ctype), [], _trace())
        text = question(_claim(ctype), verdict)
        assert text and "\n" not in text
        assert fix(_claim(ctype), verdict) == FIX_TEMPLATES[ctype]

def _ev(
    kind: EvidenceKind,
    supports: list[ClaimType],
    strength: Strength,
    path: str,
    line: int = 1,
    snippet: str = "x" * 10,
) -> Evidence:
    return Evidence(
        id=f"ev-{kind.value}-{line:03d}",
        kind=kind,
        file=path,
        line=line,
        snippet=snippet,
        supports=supports,
        strength=strength,
    )


def test_feature_terms_expands_synonym_groups() -> None:
    assert feature_terms("支持 Excel 导出") == (
        "导出",
        "export",
        "excel",
        "xlsx",
        "openpyxl",
        "workbook",
    )
    assert feature_terms("支持多语言") == ()
    assert feature_terms("用户登录") == ("登录", "login", "auth")
    assert feature_terms("统计报表") == ("统计", "statistics", "stat", "报表", "report")


def test_feature_term_groups_are_fixed() -> None:
    assert len(FEATURE_TERM_GROUPS) == 18
    assert FEATURE_TERM_GROUPS[0] == ("导出", "export")
    assert FEATURE_TERM_GROUPS[-1] == ("excel", "xlsx", "openpyxl", "workbook")


def test_feature_without_keyword_related_evidence_is_no_evidence() -> None:
    claim = _claim(ClaimType.feature, "提供数据可视化")
    evidence = [
        _ev(EvidenceKind.code, [ClaimType.feature], Strength.low, "app.py", 3, 'app = Flask(__name__)'),
        _ev(EvidenceKind.dep, [ClaimType.feature], Strength.medium, "requirements.txt", 1, "flask"),
    ]
    verdict = judge(claim, evidence, _trace())

    assert verdict.status is Status.no_evidence
    assert verdict.confidence is Confidence.low
    assert verdict.locator is None
    assert verdict.reason == "未找到与该功能关键词相关的实现"
    assert verdict.coverage is Coverage.full
    assert verdict.evidence_ids == []


def test_feature_keyword_match_keeps_evidence_but_locator_skips_dependency() -> None:
    claim = _claim(ClaimType.feature, "支持 Excel 导出")
    dep = _ev(EvidenceKind.dep, [ClaimType.feature], Strength.medium, "requirements.txt", 2, "openpyxl")
    code = _ev(EvidenceKind.code, [ClaimType.feature], Strength.low, "app.py", 5, '@app.get("/export")')
    verdict = judge(claim, [dep, code], _trace())

    assert verdict.status is Status.supported
    assert verdict.locator is not None
    assert verdict.locator.file == "app.py"
    assert verdict.evidence_ids == [dep.id, code.id]


def test_feature_without_terms_behaves_like_d1() -> None:
    claim = _claim(ClaimType.feature, "支持多语言")
    evidence = [
        _ev(EvidenceKind.code, [ClaimType.feature], Strength.low, "app.py", 5, 'app = Flask(__name__)')
    ]
    verdict = judge(claim, evidence, _trace())

    assert verdict.status is Status.supported
    assert verdict.locator is not None
    assert verdict.locator.file == "app.py"


def test_dependency_declaration_detection() -> None:
    for path in (
        "requirements.txt",
        "requirements-dev.txt",
        "pyproject.toml",
        "setup.py",
        "setup.cfg",
        "package.json",
        "poetry.lock",
        "Pipfile",
        "go.mod",
        "cargo.toml",
        "pom.xml",
        "deploy/requirements.txt",
        "deploy\\requirements-lock.txt",
    ):
        assert _is_dependency_declaration(
            _ev(EvidenceKind.dep, [ClaimType.feature], Strength.medium, path)
        ), path

    for path in ("app.py", "src/app.py", "pyproject.yml", "package/setup.yaml"):
        assert not _is_dependency_declaration(
            _ev(EvidenceKind.dep, [ClaimType.feature], Strength.medium, path)
        ), path


def test_locator_evidence_skips_dependencies_with_fallback() -> None:
    dep = _ev(EvidenceKind.dep, [ClaimType.feature], Strength.medium, "requirements.txt")
    code = _ev(EvidenceKind.code, [ClaimType.feature], Strength.low, "app.py")

    assert _locator_evidence([dep, code]) is code
    assert _locator_evidence([dep]) is dep
    assert _locator_evidence([]) is None


def test_ability_locator_skips_dependency_declaration() -> None:
    claim = _claim(ClaimType.concurrency, "支持 500 并发用户")
    dep = _ev(EvidenceKind.dep, [ClaimType.concurrency], Strength.medium, "requirements.txt", 1, "gunicorn")
    cfg = _ev(
        EvidenceKind.config,
        [ClaimType.concurrency],
        Strength.medium,
        "gunicorn.conf.py",
        3,
        "workers = 4",
    )
    verdict = judge(claim, [dep, cfg], _trace())

    assert verdict.status is Status.no_evidence
    assert "有配置，无测量" in verdict.reason
    assert verdict.locator is not None
    assert verdict.locator.file == "gunicorn.conf.py"

def test_rounds_defaults_to_one_and_is_passed_through() -> None:
    claim = _claim(ClaimType.feature)

    assert judge(claim, [], _trace()).rounds == 1
    assert judge(claim, [], _trace(), rounds=2).rounds == 2
    assert judge(claim, [], _trace(), rounds=3).rounds == 3


def test_matcher_has_no_hardcoded_rounds() -> None:
    source = Path(matcher_module.__file__).read_text(encoding="utf-8")
    assert "rounds=1" not in source