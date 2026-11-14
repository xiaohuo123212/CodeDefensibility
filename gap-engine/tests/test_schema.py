"""C-SCHEMA@1：字段一致性、序列化键与三态不变量拒绝路径。"""

import pytest

from gap_engine.schema import (
    JUDGEABLE_TYPES,
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
    is_judgeable,
)

CLAIM_KEYS = {
    "id",
    "text",
    "source",
    "type",
    "checkable",
    "uncheckable_reason",
    "out_of_scope",
    "authority",
}

EVIDENCE_KEYS = {"id", "kind", "file", "line", "snippet", "supports", "strength"}

VERDICT_KEYS = {
    "claim_id",
    "status",
    "confidence",
    "locator",
    "coverage",
    "evidence_ids",
    "reason",
    "search_trace",
    "rounds",
    "question",
    "question_priority",
    "fix",
}


def make_supported(**overrides) -> Verdict:
    kwargs = dict(
        claim_id="c1",
        status=Status.supported,
        confidence=Confidence.high,
        locator=Locator(file="app.py", line=12, snippet="app.run(threaded=True)"),
        coverage=Coverage.full,
        evidence_ids=["e1"],
        reason="线程化运行",
        search_trace=[SearchProbe(probe="run", target="threaded", scanned=1, hits=1, where=["app.py"])],
    )
    kwargs.update(overrides)
    return Verdict(**kwargs)


def make_no_evidence(**overrides) -> Verdict:
    kwargs = dict(
        claim_id="c2",
        status=Status.no_evidence,
        confidence=Confidence.medium,
        locator=None,
        coverage=Coverage.none,
        evidence_ids=[],
        reason="未找到压测文件",
        search_trace=[],
    )
    kwargs.update(overrides)
    return Verdict(**kwargs)


def test_enum_values_exact():
    assert [t.value for t in ClaimType] == [
        "performance",
        "concurrency",
        "architecture",
        "feature",
        "scale",
        "testing",
        "security",
    ]
    assert [s.value for s in Status] == ["supported", "contradicted", "no_evidence"]
    assert [c.value for c in Confidence] == ["high", "medium", "low"]
    assert [c.value for c in Coverage] == ["full", "partial", "none"]
    assert [k.value for k in EvidenceKind] == ["code", "test", "config", "dep", "comment", "bench"]
    assert [s.value for s in Strength] == ["high", "medium", "low"]


def test_judgeable_types():
    assert JUDGEABLE_TYPES == {
        ClaimType.performance,
        ClaimType.concurrency,
        ClaimType.feature,
        ClaimType.testing,
    }
    assert is_judgeable(ClaimType.concurrency) is True
    assert is_judgeable(ClaimType.architecture) is False


def test_locator_as_str():
    assert Locator(file="src/a.py", line=3).as_str() == "src/a.py:3"


def test_claim_to_dict_keys():
    claim = Claim(
        id="c1",
        text="支持 500 并发用户",
        source="README.md",
        type=ClaimType.concurrency,
        checkable=False,
        uncheckable_reason="无压测数据",
        out_of_scope=False,
    )
    data = claim.to_dict()
    assert set(data) == CLAIM_KEYS
    assert data["type"] == "concurrency"
    assert data["uncheckable_reason"] == "无压测数据"
    assert data["authority"] == "self"


def test_claim_authority_defaults_to_self():
    claim = Claim(id="c1", text="支持 Excel 导出", source="README.md", type=ClaimType.feature)
    assert claim.authority == "self"


def test_claim_authority_explicit_values():
    self_claim = Claim(
        id="c1", text="t1", source="README.md#L1", type=ClaimType.feature, authority="self"
    )
    external_claim = Claim(
        id="c2", text="t2", source="spec.md#L2", type=ClaimType.feature, authority="external"
    )
    assert self_claim.authority == "self"
    assert external_claim.authority == "external"
    assert external_claim.to_dict()["authority"] == "external"


@pytest.mark.parametrize("authority", ["", "External", "third_party", "external "])
def test_claim_authority_invalid_rejected(authority):
    with pytest.raises(ValueError, match="^claim\\.invariant: authority"):
        Claim(id="c1", text="t", source="s", type=ClaimType.feature, authority=authority)


def test_evidence_to_dict_keys():
    evidence = Evidence(
        id="e1",
        kind=EvidenceKind.config,
        file="gunicorn.conf.py",
        line=1,
        snippet="workers = 4",
        supports=[ClaimType.concurrency],
        strength=Strength.medium,
    )
    data = evidence.to_dict()
    assert set(data) == EVIDENCE_KEYS
    assert data["kind"] == "config"
    assert data["supports"] == ["concurrency"]
    assert data["strength"] == "medium"


def test_verdict_to_dict_keys_and_enums():
    data = make_supported().to_dict()
    assert set(data) == VERDICT_KEYS
    assert data["status"] == "supported"
    assert data["confidence"] == "high"
    assert data["coverage"] == "full"
    assert data["locator"] == {"file": "app.py", "line": 12, "snippet": "app.run(threaded=True)"}
    assert data["search_trace"][0]["where"] == ["app.py"]


def test_verdict_to_dict_locator_none():
    data = make_no_evidence().to_dict()
    assert data["locator"] is None
    assert data["search_trace"] == []
    assert data["rounds"] == 1
    assert data["question"] == ""
    assert data["question_priority"] == 0
    assert data["fix"] == ""


def test_supported_without_locator_rejected():
    with pytest.raises(ValueError, match="^verdict\\.invariant: supported requires locator"):
        make_supported(locator=None)


def test_contradicted_without_locator_rejected():
    with pytest.raises(ValueError, match="^verdict\\.invariant: contradicted requires locator"):
        make_supported(status=Status.contradicted, locator=None)


def test_no_evidence_empty_trace_requires_coverage_none():
    with pytest.raises(ValueError, match="^verdict\\.invariant: no_evidence without search_trace"):
        make_no_evidence(coverage=Coverage.partial)


def test_no_evidence_empty_trace_with_coverage_none_allowed():
    verdict = make_no_evidence()
    assert verdict.status is Status.no_evidence
    assert verdict.coverage is Coverage.none


def test_no_evidence_with_trace_may_be_partial():
    verdict = make_no_evidence(
        coverage=Coverage.partial,
        search_trace=[
            SearchProbe(probe="bench", target="locust", scanned=0, hits=0, where=["."]),
        ],
    )
    assert verdict.coverage is Coverage.partial


def test_unknown_status_rejected():
    with pytest.raises(ValueError, match="^verdict\\.invariant: unknown enum value"):
        make_no_evidence(status="unsure")


def test_claim_and_evidence_are_frozen():
    claim = Claim(id="c1", text="t", source="s", type=ClaimType.feature)
    evidence = Evidence(
        id="e1",
        kind=EvidenceKind.code,
        file="app.py",
        line=1,
        snippet="x",
        supports=[ClaimType.feature],
        strength=Strength.high,
    )
    with pytest.raises(Exception):
        claim.text = "changed"
    with pytest.raises(Exception):
        evidence.line = 2