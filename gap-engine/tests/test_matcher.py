"""三态判定、缺口标签与追问/补齐文案的单元测试（C-MATCHER@2 / C-MATCHER@4）。"""

from __future__ import annotations

from pathlib import Path

import gap_engine.matcher as matcher_module
from gap_engine.extractors.negation import NEGATION_MARKERS
from gap_engine.matcher import (
    CONTRADICTED_FIX,
    CONTRADICTED_QUESTION_TEMPLATE,
    FIX_TEMPLATES,
    LOCAL_COMPLETION_PROMPT,
    QUESTION_TEMPLATES,
    FEATURE_TERM_GROUPS,
    IMPL_TERM_GROUPS,
    _is_dependency_declaration,
    _is_negation,
    _locator_evidence,
    claim_terms,
    feature_terms,
    fix,
    gap_label,
    impl_terms,
    judge,
    mentions,
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


def test_feature_without_feature_terms_falls_back_to_claim_terms() -> None:
    claim = _claim(ClaimType.feature)
    assert feature_terms(claim.text) == ()
    assert claim_terms(claim.text) == ("某能力",)

    evidence = [_evidence(EvidenceKind.code, [ClaimType.feature], Strength.low, "app.py", 5)]
    verdict = judge(claim, evidence, _trace())
    assert verdict.status is Status.no_evidence
    assert verdict.confidence is Confidence.low
    assert verdict.locator is None
    assert verdict.evidence_ids == []
    assert verdict.reason == "未找到与该功能关键词相关的实现"
    assert verdict.search_trace == _trace()
    assert verdict.rounds == 1

    evidence.append(_evidence(EvidenceKind.dep, [ClaimType.feature], Strength.medium, "req.txt", 2))
    assert judge(claim, evidence, _trace()).status is Status.no_evidence


def test_judge_without_negation_markers_keeps_original_statuses() -> None:
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


def test_feature_without_any_terms_is_no_evidence() -> None:
    claim = _claim(ClaimType.feature, "支持")
    assert feature_terms(claim.text) == ()
    assert claim_terms(claim.text) == ()

    evidence = [
        _ev(EvidenceKind.code, [ClaimType.feature], Strength.low, "app.py", 5, 'app = Flask(__name__)')
    ]
    verdict = judge(claim, evidence, _trace())

    assert verdict.status is Status.no_evidence
    assert verdict.confidence is Confidence.low
    assert verdict.locator is None
    assert verdict.evidence_ids == []
    assert verdict.reason == "需求文本无可用于匹配的关键词"
    assert verdict.coverage is Coverage.full


def test_feature_fallback_terms_keep_matching_evidence_supported() -> None:
    claim = _claim(ClaimType.feature, "支持多语言")
    evidence = [
        _ev(EvidenceKind.code, [ClaimType.feature], Strength.low, "i18n.py", 3, "多语言资源已加载")
    ]
    verdict = judge(claim, evidence, _trace())

    assert verdict.status is Status.supported
    assert verdict.locator is not None
    assert verdict.locator.file == "i18n.py"


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


def test_claim_terms_keeps_significant_words() -> None:
    assert claim_terms("支持 Excel 导出") == ("excel", "导出")
    assert claim_terms("支持 500 并发用户") == ("500", "并发")
    assert claim_terms("支持多语言") == ("多语言",)
    assert claim_terms("支持超长中文词组测试") == ("超长中文词组",)
    assert claim_terms("支持") == ()
    assert claim_terms("") == ()


def test_is_negation_reuses_extractor_markers() -> None:
    assert matcher_module.NEGATION_MARKERS is NEGATION_MARKERS

    assert _is_negation(_ev(EvidenceKind.code, [ClaimType.feature], Strength.high, "app.py", 1, "导出功能暂未实现"))
    assert _is_negation(_ev(EvidenceKind.code, [ClaimType.feature], Strength.high, "app.py", 2, "Not Supported"))
    assert not _is_negation(_ev(EvidenceKind.code, [ClaimType.feature], Strength.high, "app.py", 3, '@app.get("/export")'))
    assert not _is_negation(_ev(EvidenceKind.code, [ClaimType.feature], Strength.high, "app.py", 4, ""))


def test_contradiction_with_supporting_evidence_is_contradicted() -> None:
    claim = _claim(ClaimType.feature, "支持 Excel 导出")
    support = _ev(EvidenceKind.code, [ClaimType.feature], Strength.low, "app.py", 5, '@app.get("/export")')
    negation = _ev(EvidenceKind.code, [ClaimType.feature], Strength.high, "app.py", 9, "导出功能暂未实现")

    verdict = judge(claim, [support, negation], _trace())

    assert verdict.status is Status.contradicted
    assert verdict.confidence is Confidence.high
    assert verdict.locator is not None
    assert (verdict.locator.file, verdict.locator.line) == ("app.py", 9)
    assert "反证" in verdict.reason
    assert "另有 1 处支持痕迹" in verdict.reason
    assert verdict.evidence_ids == [support.id, negation.id]


def test_negation_without_usable_line_falls_back_to_original_flow() -> None:
    claim = _claim(ClaimType.concurrency, "支持 500 并发用户")
    negation = Evidence(
        id="ev-negation-001",
        kind=EvidenceKind.code,
        file="app.py",
        line=None,  # type: ignore[arg-type]
        snippet="500 并发暂未实现",
        supports=[ClaimType.concurrency],
        strength=Strength.high,
    )

    verdict = judge(claim, [negation], _trace())

    assert verdict.status is not Status.contradicted
    assert verdict.status is Status.no_evidence
    assert "有配置，无测量" in verdict.reason


def test_unrelated_negation_does_not_contradict() -> None:
    claim = _claim(ClaimType.feature, "支持 Excel 导出")
    support = _ev(EvidenceKind.code, [ClaimType.feature], Strength.low, "app.py", 5, '@app.get("/export")')
    unrelated = _ev(EvidenceKind.code, [ClaimType.feature], Strength.high, "app.py", 11, "不支持 Windows 7")

    verdict = judge(claim, [support, unrelated], _trace())

    assert verdict.status is Status.supported
    assert verdict.locator is not None
    assert verdict.locator.line == 5


def test_contradicted_labels_and_texts() -> None:
    claim = _claim(ClaimType.feature, "支持 Excel 导出")
    negation = _ev(EvidenceKind.code, [ClaimType.feature], Strength.high, "app.py", 9, "导出功能暂未实现")

    verdict = judge(claim, [negation], _trace())

    assert verdict.status is Status.contradicted
    assert gap_label(claim, verdict) == "该改"
    assert fix(claim, verdict) == CONTRADICTED_FIX
    assert CONTRADICTED_FIX == (
        "代码与要求不一致：先确认这条要求是否仍然有效；"
        "有效就改实现，无效就改需求文档，不要两边都留着。"
    )
    assert question(claim, verdict) == CONTRADICTED_QUESTION_TEMPLATE.format(text=claim.text)


def test_matcher_docstring_no_longer_promises_no_contradicted() -> None:
    source = Path(matcher_module.__file__).read_text(encoding="utf-8")
    assert "永不产出" not in source

def test_mentions_requires_ascii_word_boundary() -> None:
    noise = _ev(
        EvidenceKind.code,
        [ClaimType.feature],
        Strength.low,
        "editors/vscode/runtime/Lib/logging/__init__.py",
        126,
        "def getLevelNamesMapping():",
    )
    assert not mentions(noise, ("eln",))

    real = _ev(
        EvidenceKind.code,
        [ClaimType.feature],
        Strength.low,
        "tests/cases/test_alloc_and_sizes.py",
        23,
        "def _run(eln, tu, *args):",
    )
    assert mentions(real, ("eln",))

    route = _ev(EvidenceKind.code, [ClaimType.feature], Strength.low, "app.py", 7, '@app.get("/export")')
    assert mentions(route, ("export",))
    assert not mentions(route, ("xport",))


def test_mentions_keeps_cjk_substring_matching() -> None:
    ev = _ev(EvidenceKind.code, [ClaimType.feature], Strength.low, "i18n.py", 3, "多语言资源已加载")

    assert mentions(ev, ("多语言",))


def test_impl_term_groups_are_fixed() -> None:
    assert len(IMPL_TERM_GROUPS) == 21
    assert IMPL_TERM_GROUPS[0] == ("协程", "coroutine")
    # 锁相关词故意不收：``lock`` 在 filelock 代码里遍地都是，会把误报抬回去
    assert ("锁", "lock", "flock") not in IMPL_TERM_GROUPS


def test_impl_terms_expands_cjk_requirement_to_english_impl_words() -> None:
    assert impl_terms("支持用同步 with 语句加锁") == ("同步 with", "sync", "synchronous")
    assert impl_terms("签名分隔符可以自由指定") == ("分隔符", "sep", "separator")
    assert impl_terms("支持多语言") == ()
    # ASCII 触发词按 C-MATCHER@6 词边界：AsyncFileLock 里的 sync 不算独立词
    assert impl_terms("AsyncFileLock 支持自定义 executor") == ()
    assert impl_terms("AsyncFileLock 支持 async/await") == ("异步", "async", "await")


def test_impl_terms_find_english_negation_for_sync_with_requirement() -> None:
    claim = _claim(ClaimType.feature, "AsyncFileLock 支持用同步 with 语句加锁")
    negation = _ev(
        EvidenceKind.code,
        [ClaimType.feature],
        Strength.high,
        "src/filelock/asyncio.py",
        317,
        "Sync context manager entry is not supported because lock acquisition is a coroutine.",
    )

    verdict = judge(claim, [negation], _trace())

    assert verdict.status is Status.contradicted
    assert verdict.locator is not None
    assert (verdict.locator.file, verdict.locator.line) == ("src/filelock/asyncio.py", 317)


def test_impl_terms_find_negation_by_separator() -> None:
    claim = _claim(ClaimType.feature, "签名分隔符可以自由指定")
    support = _ev(EvidenceKind.code, [ClaimType.feature], Strength.low, "signer.py", 140, "self.sep = want_bytes(sep)")
    negation = _ev(
        EvidenceKind.code,
        [ClaimType.feature],
        Strength.high,
        "signer.py",
        147,
        "The given separator is not supported because it may be contained in the signature itself.",
    )

    verdict = judge(claim, [support, negation], _trace())

    assert verdict.status is Status.contradicted
    assert verdict.locator is not None
    assert verdict.locator.line == 147


def test_impl_terms_do_not_admit_unrelated_negation() -> None:
    claim = _claim(ClaimType.feature, "AsyncFileLock 支持用同步 with 语句加锁")
    support = _ev(EvidenceKind.code, [ClaimType.feature], Strength.low, "src/filelock/asyncio.py", 330, "with AsyncFileLock(target) as lock:")
    unrelated = _ev(
        EvidenceKind.code,
        [ClaimType.feature],
        Strength.high,
        "src/filelock/asyncio.py",
        900,
        "Windows named pipes are not supported on this platform version",
    )

    verdict = judge(claim, [support, unrelated], _trace())

    assert verdict.status is Status.supported
    assert verdict.locator is not None
    assert verdict.locator.line == 330

def test_negation_relevance_ignores_file_path_package_name() -> None:
    # C-MATCHER@8：``src/filelock/`` 路径命中 terms 里的 ``filelock``，不能让一行
    # 讲 Termux 无 os.link 的注释变成「lifetime 过期」的反证
    claim = _claim(ClaimType.feature, "FileLock 支持用 lifetime 参数按文件年龄强制过期")
    support = _ev(
        EvidenceKind.code,
        [ClaimType.feature],
        Strength.medium,
        "src/filelock/_api.py",
        120,
        "def __init__(self, lock_file, *, lifetime: float | None = None) -> None:",
    )
    unrelated = _ev(
        EvidenceKind.code,
        [ClaimType.feature],
        Strength.high,
        "src/filelock/_strict.py",
        830,
        "# No os.link at all (Termux/Android): report it as unsupported like a filesystem that refuses hard links",
    )

    verdict = judge(claim, [support, unrelated], _trace())

    assert verdict.status is Status.supported
    assert verdict.locator is not None
    assert verdict.locator.line == 120


def test_negation_relevance_ignores_generic_literal_terms() -> None:
    # C-MATCHER@8：``preserve_lock_file=True`` 切出的 ``true`` 无区分度，
    # 不能让 pytest 参数标识 ``id="unsupported"`` 变成反证
    claim = _claim(ClaimType.feature, "SoftFileLock 支持 preserve_lock_file=True 保留锁文件")
    support = _ev(
        EvidenceKind.code,
        [ClaimType.feature],
        Strength.medium,
        "src/filelock/_api.py",
        200,
        "if not preserve_lock_file: self._release()",
    )
    unrelated = _ev(
        EvidenceKind.code,
        [ClaimType.feature],
        Strength.high,
        "tests/test_util.py",
        613,
        '@pytest.mark.parametrize("effective_ids", [pytest.param(True, id="supported"), pytest.param(False, id="unsupported")])',
    )

    verdict = judge(claim, [support, unrelated], _trace())

    assert verdict.status is Status.supported

def test_mentions_uses_file_name_not_directory() -> None:
    # C-MATCHER@9：目录名里的包名不能让人人恒命中
    packaged = _ev(EvidenceKind.code, [ClaimType.feature], Strength.low, "src/filelock/_api.py", 1, "return None")
    assert not mentions(packaged, ("filelock",))
    assert not mentions(packaged, ("src",))

    named = _ev(EvidenceKind.code, [ClaimType.feature], Strength.low, "src/pkg/cli.py", 1, "return None")
    assert mentions(named, ("cli",))


def test_feature_judgment_does_not_match_package_name_in_path() -> None:
    # C-MATCHER@9：只有包名与需求重合、内容无关的证据不能支撑结论
    claim = _claim(ClaimType.feature, "FileLock 支持用 lifetime 参数按文件年龄强制过期")
    unrelated = _ev(
        EvidenceKind.code,
        [ClaimType.feature],
        Strength.high,
        "src/filelock/_strict.py",
        830,
        "# No os.link at all (Termux/Android): report it as unsupported like a filesystem that refuses hard links",
    )

    verdict = judge(claim, [unrelated], _trace())

    assert verdict.status is Status.no_evidence
    assert verdict.locator is None
