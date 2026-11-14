"""问题优先级计算与稳定排序键（C-PRIORITY@1）。"""

from __future__ import annotations

from .schema import Confidence, Status, Verdict

STATUS_WEIGHT: dict[Status, int] = {
    Status.no_evidence: 3,
    Status.contradicted: 2,
    Status.supported: 1,
}

CONFIDENCE_WEIGHT: dict[Confidence, int] = {
    Confidence.low: 3,
    Confidence.medium: 2,
    Confidence.high: 1,
}


def compute_question_priority(status: Status, confidence: Confidence) -> int:
    raw = STATUS_WEIGHT[status] + CONFIDENCE_WEIGHT[confidence]
    return int((raw - 2) * 2.5 + 0.5)


def sort_key(v: Verdict) -> tuple[int, str]:
    return (-compute_question_priority(v.status, v.confidence), v.claim_id)