"""同类项目普遍性先验（C-BASELINE@1）。

双条件缺口的第二条件：缺证据之外，还要求"同类项目普遍具备"。
D1–D3 用先验值，D4 换成实测 ``reports/prevalence.json``，报告须标注来源。
"""

from __future__ import annotations

import json
from pathlib import Path

from .schema import ClaimType

PREVALENCE: dict[ClaimType, float] = {
    ClaimType.performance: 0.30,
    ClaimType.concurrency: 0.50,
    ClaimType.testing: 0.80,
    ClaimType.feature: 0.90,
    ClaimType.architecture: 0.60,
    ClaimType.scale: 0.40,
    ClaimType.security: 0.50,
}

PREVALENCE_THRESHOLD: float = 0.5


def is_prevalent(t: ClaimType, prevalence: dict[ClaimType, float] | None = None) -> bool:
    table = PREVALENCE if prevalence is None else prevalence
    return table.get(t, PREVALENCE[t]) >= PREVALENCE_THRESHOLD


def load_prevalence(path: Path) -> dict[ClaimType, float]:
    table = dict(PREVALENCE)
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return table
    if not isinstance(raw, dict):
        return table

    for key, value in raw.items():
        try:
            claim_type = ClaimType(key)
        except ValueError:
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        ratio = float(value)
        if 0.0 <= ratio <= 1.0:
            table[claim_type] = ratio
    return table