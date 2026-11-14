"""C-PRIORITY@1：权重表、映射区间与同分排序稳定性。"""

import pytest

from gap_engine.priority import (
    CONFIDENCE_WEIGHT,
    STATUS_WEIGHT,
    compute_question_priority,
    sort_key,
    weight_breakdown,
)
from gap_engine.schema import Confidence, Coverage, Status, Verdict


def make_verdict(claim_id: str, status: Status, confidence: Confidence) -> Verdict:
    from gap_engine.schema import Locator

    return Verdict(
        claim_id=claim_id,
        status=status,
        confidence=confidence,
        locator=Locator(file="app.py", line=1) if status is not Status.no_evidence else None,
        coverage=Coverage.full if status is not Status.no_evidence else Coverage.none,
        evidence_ids=[],
        reason="",
        search_trace=[],
    )


def test_weight_tables():
    assert STATUS_WEIGHT == {
        Status.no_evidence: 3,
        Status.contradicted: 2,
        Status.supported: 1,
    }
    assert CONFIDENCE_WEIGHT == {
        Confidence.low: 3,
        Confidence.medium: 2,
        Confidence.high: 1,
    }


@pytest.mark.parametrize(
    ("status", "confidence", "expected"),
    [
        (Status.supported, Confidence.high, 0),
        (Status.supported, Confidence.medium, 3),
        (Status.supported, Confidence.low, 5),
        (Status.contradicted, Confidence.high, 3),
        (Status.contradicted, Confidence.medium, 5),
        (Status.contradicted, Confidence.low, 8),
        (Status.no_evidence, Confidence.high, 5),
        (Status.no_evidence, Confidence.medium, 8),
        (Status.no_evidence, Confidence.low, 10),
    ],
)
def test_priority_mapping(status, confidence, expected):
    actual = compute_question_priority(status, confidence)
    assert actual == expected
    assert isinstance(actual, int)
    assert 0 <= actual <= 10


def test_priority_unknown_enum_raises_keyerror():
    with pytest.raises(KeyError):
        compute_question_priority("bogus", Confidence.high)
    with pytest.raises(KeyError):
        compute_question_priority(Status.no_evidence, "bogus")


def test_sort_key_shape():
    verdict = make_verdict("c7", Status.no_evidence, Confidence.low)
    assert sort_key(verdict) == (-10, "c7")


def test_sort_puts_high_priority_first():
    verdicts = [
        make_verdict("c1", Status.supported, Confidence.high),
        make_verdict("c2", Status.no_evidence, Confidence.low),
        make_verdict("c3", Status.contradicted, Confidence.medium),
    ]
    ordered = sorted(verdicts, key=sort_key)
    assert [v.claim_id for v in ordered] == ["c2", "c3", "c1"]


def test_sort_is_stable_on_equal_priority_by_claim_id():
    verdicts = [
        make_verdict("c-b", Status.no_evidence, Confidence.medium),
        make_verdict("c-a", Status.contradicted, Confidence.low),
        make_verdict("c-c", Status.no_evidence, Confidence.medium),
    ]
    assert {compute_question_priority(v.status, v.confidence) for v in verdicts} == {8}
    ordered = sorted(verdicts, key=sort_key)
    assert [v.claim_id for v in ordered] == ["c-a", "c-b", "c-c"]
    assert ordered == sorted(reversed(verdicts), key=sort_key)

@pytest.mark.parametrize("status", list(Status))
@pytest.mark.parametrize("confidence", list(Confidence))
def test_weight_breakdown_matches_tables(status, confidence):
    assert weight_breakdown(status, confidence) == (
        STATUS_WEIGHT[status],
        CONFIDENCE_WEIGHT[confidence],
    )


@pytest.mark.parametrize("status", list(Status))
@pytest.mark.parametrize("confidence", list(Confidence))
def test_weight_breakdown_sums_to_question_priority(status, confidence):
    raw = sum(weight_breakdown(status, confidence))
    assert compute_question_priority(status, confidence) == int((raw - 2) * 2.5 + 0.5)


def test_weight_breakdown_unknown_enum_raises_keyerror():
    with pytest.raises(KeyError):
        weight_breakdown("bogus", Confidence.high)
    with pytest.raises(KeyError):
        weight_breakdown(Status.no_evidence, "bogus")