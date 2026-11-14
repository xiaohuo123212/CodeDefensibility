"""回执解析与七指标（C-REVIEW@1）。

回执是独立的 JSON Lines 输入，不进入 ``Verdict``；本模块只依赖 ``schema`` 与
``metrics._rate``，因此可用构造数据在无仓库场景下测试。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .metrics import _rate
from .schema import Claim, Coverage, Status, Verdict, is_judgeable

VERDICT_VALUES: frozenset[str] = frozenset({"对", "错", "说不清"})

RECEIPT_KEYS: tuple[str, ...] = (
    "n_receipts",
    "n_valid",
    "n_agree",
    "n_disagree",
    "n_unclear",
    "n_falsifiable_dispute",
    "n_asserted",
    "n_asserted_located",
    "n_silent",
    "n_fn",
    "n_fp",
    "n_all_output",
    "n_all_judgeable",
    "author_approval_rate",
    "locator_rate",
    "false_negative_rate",
    "false_positive_rate",
    "unfalsifiable_rate",
    "unclear_rate",
    "uncovered_rate",
)


@dataclass(frozen=True)
class Receipt:
    claim_id: str
    verdict: str
    evidence: str = ""


def load_receipts(path: Path) -> list[Receipt]:
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    receipts: list[Receipt] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(item, dict):
            continue

        claim_id = item.get("claim_id")
        verdict = item.get("author_verdict")
        evidence = item.get("author_evidence", "")
        if not isinstance(claim_id, str) or not claim_id:
            continue
        if not isinstance(verdict, str) or verdict not in VERDICT_VALUES:
            continue
        if not isinstance(evidence, str):
            continue
        receipts.append(Receipt(claim_id=claim_id, verdict=verdict, evidence=evidence))
    return receipts


def _is_blank(value: str) -> bool:
    return not value.strip()


def score(
    claims: list[Claim], verdicts: list[Verdict], receipts: list[Receipt]
) -> dict[str, int | float]:
    claim_by_id = {claim.id: claim for claim in claims}
    verdict_by_id = {verdict.claim_id: verdict for verdict in verdicts}

    valid: list[tuple[Receipt, Verdict]] = []
    for receipt in receipts:
        claim = claim_by_id.get(receipt.claim_id)
        verdict = verdict_by_id.get(receipt.claim_id)
        if claim is None or verdict is None:
            continue
        if not is_judgeable(claim.type) or claim.out_of_scope:
            continue
        if verdict.coverage is Coverage.none:
            continue
        valid.append((receipt, verdict))

    n_agree = sum(1 for receipt, _ in valid if receipt.verdict == "对")
    n_disagree = sum(1 for receipt, _ in valid if receipt.verdict == "错")
    n_unclear = sum(1 for receipt, _ in valid if receipt.verdict == "说不清")
    n_falsifiable_dispute = sum(
        1 for receipt, _ in valid if receipt.verdict == "错" and _is_blank(receipt.evidence)
    )
    n_asserted = sum(
        1
        for _, verdict in valid
        if verdict.status in (Status.supported, Status.contradicted)
    )
    n_asserted_located = sum(
        1
        for _, verdict in valid
        if verdict.status in (Status.supported, Status.contradicted)
        and verdict.locator is not None
    )
    n_silent = sum(1 for _, verdict in valid if verdict.status is Status.no_evidence)
    n_fn = sum(
        1
        for receipt, verdict in valid
        if verdict.status is Status.no_evidence
        and receipt.verdict == "错"
        and not _is_blank(receipt.evidence)
    )
    n_fp = sum(
        1
        for receipt, verdict in valid
        if verdict.status in (Status.supported, Status.contradicted)
        and receipt.verdict == "错"
    )
    n_all_output = sum(1 for verdict in verdicts if verdict.coverage is Coverage.none)
    n_all_judgeable = sum(
        1
        for verdict in verdicts
        if (claim := claim_by_id.get(verdict.claim_id)) is not None
        and is_judgeable(claim.type)
        and not claim.out_of_scope
    )

    n_valid = len(valid)
    return {
        "n_receipts": len(receipts),
        "n_valid": n_valid,
        "n_agree": n_agree,
        "n_disagree": n_disagree,
        "n_unclear": n_unclear,
        "n_falsifiable_dispute": n_falsifiable_dispute,
        "n_asserted": n_asserted,
        "n_asserted_located": n_asserted_located,
        "n_silent": n_silent,
        "n_fn": n_fn,
        "n_fp": n_fp,
        "n_all_output": n_all_output,
        "n_all_judgeable": n_all_judgeable,
        "author_approval_rate": _rate(n_agree, n_agree + n_disagree),
        "locator_rate": _rate(n_asserted_located, n_asserted),
        "false_negative_rate": _rate(n_fn, n_silent),
        "false_positive_rate": _rate(n_fp, n_asserted),
        "unfalsifiable_rate": _rate(n_falsifiable_dispute, n_valid),
        "unclear_rate": _rate(n_unclear, n_valid),
        "uncovered_rate": _rate(n_all_output, n_all_judgeable),
    }