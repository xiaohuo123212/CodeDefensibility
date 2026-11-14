"""机器可读指标（C-METRICS@1）。

键固定 12 个；分母为 0 时比率取 ``0.0``；比率保留 4 位小数。
"""

from __future__ import annotations

from .schema import Claim, Coverage, Status, Verdict, is_judgeable

METRIC_KEYS: tuple[str, ...] = (
    "n_claims",
    "n_judgeable",
    "n_supported",
    "n_no_evidence",
    "n_contradicted",
    "locator_rate",
    "no_evidence_rate",
    "coverage_none_rate",
    "audit_effort_classes",
    "audit_effort_scanned",
    "audit_effort_mean_classes",
    "audit_effort_mean_scanned",
)


def _rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def compute(claims: list[Claim], verdicts: list[Verdict]) -> dict[str, int | float]:
    claim_by_id = {claim.id: claim for claim in claims}
    scoped = [
        verdict
        for verdict in verdicts
        if verdict.claim_id in claim_by_id
        and is_judgeable(claim_by_id[verdict.claim_id].type)
        and not claim_by_id[verdict.claim_id].out_of_scope
    ]

    n_judgeable = len(scoped)
    n_supported = sum(1 for v in scoped if v.status is Status.supported)
    n_no_evidence = sum(1 for v in scoped if v.status is Status.no_evidence)
    n_contradicted = sum(1 for v in scoped if v.status is Status.contradicted)
    n_located = sum(
        1
        for v in scoped
        if v.status in (Status.supported, Status.contradicted) and v.locator is not None
    )
    n_coverage_none = sum(1 for v in scoped if v.coverage is Coverage.none)

    total_classes = sum(len(v.search_trace) for v in scoped)
    total_scanned = sum(p.scanned for v in scoped for p in v.search_trace)

    return {
        "n_claims": len(claims),
        "n_judgeable": n_judgeable,
        "n_supported": n_supported,
        "n_no_evidence": n_no_evidence,
        "n_contradicted": n_contradicted,
        "locator_rate": _rate(n_located, n_supported + n_contradicted),
        "no_evidence_rate": _rate(n_no_evidence, n_judgeable),
        "coverage_none_rate": _rate(n_coverage_none, n_judgeable),
        "audit_effort_classes": total_classes,
        "audit_effort_scanned": total_scanned,
        "audit_effort_mean_classes": _rate(total_classes, n_judgeable),
        "audit_effort_mean_scanned": _rate(total_scanned, n_judgeable),
    }