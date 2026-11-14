"""同类项目普遍性先验（C-BASELINE@1/@2）。

双条件缺口的第二条件：缺证据之外，还要求"同类项目普遍具备"。
D1–D3 用先验值，D4 起可换成实测 ``reports/prevalence.json``，报告须标注来源。
实测文件是 ``{"<type>": {"n_claims", "n_prevalent", "prevalence"}}`` 嵌套结构，
手工文件是 ``{"<type>": 0.5}`` 扁平结构，两者读回同一个 ``dict[ClaimType, float]``。
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


def _accepted_ratio(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, dict):
        candidate = value.get("prevalence")
        if isinstance(candidate, bool) or not isinstance(candidate, (int, float)):
            return None
        ratio = float(candidate)
    elif isinstance(value, (int, float)):
        ratio = float(value)
    else:
        return None
    return ratio if 0.0 <= ratio <= 1.0 else None


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
        ratio = _accepted_ratio(value)
        if ratio is None:
            continue
        table[claim_type] = ratio
    return table