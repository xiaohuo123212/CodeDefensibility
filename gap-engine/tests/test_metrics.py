"""指标计算测试（C-METRICS@1）。"""

from __future__ import annotations

from gap_engine.metrics import METRIC_KEYS, compute
from gap_engine.schema import (
    Claim,
    ClaimType,
    Confidence,
    Coverage,
    Locator,
    SearchProbe,
    Status,
    Verdict,
)


def _claim(cid: str, ctype: ClaimType, out_of_scope: bool = False) -> Claim:
    return Claim(
        id=cid,
        text=f"claim {cid}",
        source="readme",
        type=ctype,
        out_of_scope=out_of_scope,
    )


def _verdict(
    cid: str,
    status: Status,
    coverage: Coverage = Coverage.partial,
    locator: Locator | None = None,
    trace: list[SearchProbe] | None = None,
) -> Verdict:
    return Verdict(
        claim_id=cid,
        status=status,
        confidence=Confidence.high if status is Status.supported else Confidence.low,
        locator=locator,
        coverage=coverage,
        evidence_ids=[],
        reason="",
        search_trace=_trace() if trace is None else trace,
    )


def _trace() -> list[SearchProbe]:
    return [
        SearchProbe(probe="a", target="t", scanned=2, hits=1, where=["app.py:1"]),
        SearchProbe(probe="b", target="t", scanned=3, hits=0, where=[]),
    ]


def test_keys_are_fixed() -> None:
    metrics = compute([], [])
    assert set(metrics) == set(METRIC_KEYS)
    assert len(METRIC_KEYS) == 12


def test_empty_inputs_give_zero_rates() -> None:
    metrics = compute([], [])
    assert metrics["n_claims"] == 0
    assert metrics["n_judgeable"] == 0
    assert metrics["locator_rate"] == 0.0
    assert metrics["no_evidence_rate"] == 0.0
    assert metrics["coverage_none_rate"] == 0.0
    assert metrics["audit_effort_mean_classes"] == 0.0
    assert metrics["audit_effort_mean_scanned"] == 0.0


def test_rates_and_audit_effort() -> None:
    claims = [
        _claim("c01", ClaimType.feature),
        _claim("c02", ClaimType.performance),
        _claim("c03", ClaimType.testing),
        _claim("c04", ClaimType.architecture),
        _claim("c05", ClaimType.scale, out_of_scope=True),
    ]
    verdicts = [
        _verdict("c01", Status.supported, Coverage.full, Locator("app.py", 1)),
        _verdict("c02", Status.no_evidence),
        _verdict("c03", Status.no_evidence, Coverage.none),
        _verdict("c04", Status.supported, Coverage.partial, Locator("app.py", 2)),
        _verdict("c05", Status.no_evidence),
    ]
    metrics = compute(claims, verdicts)

    assert metrics["n_claims"] == 5
    assert metrics["n_judgeable"] == 3
    assert metrics["n_supported"] == 1
    assert metrics["n_no_evidence"] == 2
    assert metrics["n_contradicted"] == 0
    assert metrics["locator_rate"] == 1.0
    assert metrics["no_evidence_rate"] == round(2 / 3, 4)
    assert metrics["coverage_none_rate"] == round(1 / 3, 4)
    assert metrics["audit_effort_classes"] == 6
    assert metrics["audit_effort_scanned"] == 15
    assert metrics["audit_effort_mean_classes"] == 2.0
    assert metrics["audit_effort_mean_scanned"] == 5.0


def test_mismatched_lists_use_intersection() -> None:
    claims = [_claim("c01", ClaimType.feature)]
    verdicts = [
        _verdict("c01", Status.supported, locator=Locator("app.py", 1)),
        _verdict("c99", Status.no_evidence),
    ]
    metrics = compute(claims, verdicts)
    assert metrics["n_judgeable"] == 1
    assert metrics["n_supported"] == 1
    assert metrics["n_no_evidence"] == 0