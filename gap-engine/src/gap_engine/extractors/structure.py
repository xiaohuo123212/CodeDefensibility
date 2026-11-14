"""structure 抽取器：文件数、总行数、最大文件（至多 3 条）。"""

from __future__ import annotations

from ..index import RepoIndex
from ..schema import ClaimType, Evidence, EvidenceKind, Strength
from . import _evidence

SUPPORTS = [ClaimType.feature]


def extract(index: RepoIndex) -> list[Evidence]:
    if not index.files:
        return []

    texts = index.text()
    lines = {index.rel(p): len(texts.get(index.rel(p), "").splitlines()) for p in index.files}
    total = sum(lines.values())
    biggest = max(index.files, key=lambda p: lines[index.rel(p)])
    biggest_rel = index.rel(biggest)

    return [
        _evidence(
            "structure",
            1,
            EvidenceKind.code,
            biggest_rel,
            1,
            f"files={len(index.files)} indexed",
            SUPPORTS,
            Strength.low,
        ),
        _evidence(
            "structure",
            2,
            EvidenceKind.code,
            biggest_rel,
            1,
            f"loc={total} lines in total",
            SUPPORTS,
            Strength.low,
        ),
        _evidence(
            "structure",
            3,
            EvidenceKind.code,
            biggest_rel,
            1,
            f"largest={biggest_rel} ({lines[biggest_rel]} lines)",
            SUPPORTS,
            Strength.low,
        ),
    ]