"""数据模型与三态判定不变量（C-SCHEMA@1）。

字段名与《施工图-对账引擎》§1.2 一一对应，不设别名；枚举值即 JSON 值。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

INVARIANT_PREFIX = "verdict.invariant:"


class ClaimType(str, Enum):
    performance = "performance"
    concurrency = "concurrency"
    architecture = "architecture"
    feature = "feature"
    scale = "scale"
    testing = "testing"
    security = "security"


JUDGEABLE_TYPES: frozenset[ClaimType] = frozenset(
    {
        ClaimType.performance,
        ClaimType.concurrency,
        ClaimType.feature,
        ClaimType.testing,
    }
)


def is_judgeable(t: ClaimType) -> bool:
    return t in JUDGEABLE_TYPES


class Status(str, Enum):
    supported = "supported"
    contradicted = "contradicted"
    no_evidence = "no_evidence"


class Confidence(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class Coverage(str, Enum):
    full = "full"
    partial = "partial"
    none = "none"


class EvidenceKind(str, Enum):
    code = "code"
    test = "test"
    config = "config"
    dep = "dep"
    comment = "comment"
    bench = "bench"


class Strength(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


def _value(item: object) -> object:
    return item.value if isinstance(item, Enum) else item


@dataclass(frozen=True)
class Locator:
    file: str
    line: int
    snippet: str | None = None

    def as_str(self) -> str:
        return f"{self.file}:{self.line}"

    def to_dict(self) -> dict:
        return {"file": self.file, "line": self.line, "snippet": self.snippet}


@dataclass(frozen=True)
class Claim:
    id: str
    text: str
    source: str
    type: ClaimType
    checkable: bool = True
    uncheckable_reason: str | None = None
    out_of_scope: bool = False
    authority: str = "self"

    def __post_init__(self) -> None:
        if self.authority not in ("self", "external"):
            raise ValueError(
                "claim.invariant: authority must be 'self' or 'external', "
                f"got {self.authority!r}"
            )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "text": self.text,
            "source": self.source,
            "type": _value(self.type),
            "checkable": self.checkable,
            "uncheckable_reason": self.uncheckable_reason,
            "out_of_scope": self.out_of_scope,
            "authority": self.authority,
        }


@dataclass(frozen=True)
class Evidence:
    id: str
    kind: EvidenceKind
    file: str
    line: int
    snippet: str
    supports: list[ClaimType]
    strength: Strength

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "kind": _value(self.kind),
            "file": self.file,
            "line": self.line,
            "snippet": self.snippet,
            "supports": [_value(t) for t in self.supports],
            "strength": _value(self.strength),
        }


@dataclass(frozen=True)
class SearchProbe:
    probe: str
    target: str
    scanned: int
    hits: int
    where: list[str]

    def to_dict(self) -> dict:
        return {
            "probe": self.probe,
            "target": self.target,
            "scanned": self.scanned,
            "hits": self.hits,
            "where": list(self.where),
        }


@dataclass
class Verdict:
    claim_id: str
    status: Status
    confidence: Confidence
    locator: Locator | None
    coverage: Coverage
    evidence_ids: list[str]
    reason: str
    search_trace: list[SearchProbe]
    rounds: int = 1
    question: str = ""
    question_priority: int = 0
    fix: str = ""

    def __post_init__(self) -> None:
        try:
            self.status = Status(self.status)
            self.confidence = Confidence(self.confidence)
            self.coverage = Coverage(self.coverage)
        except ValueError as exc:
            raise ValueError(f"{INVARIANT_PREFIX} unknown enum value ({exc})") from exc

        if self.status in (Status.supported, Status.contradicted) and self.locator is None:
            raise ValueError(f"{INVARIANT_PREFIX} {self.status.value} requires locator")

        if (
            self.status is Status.no_evidence
            and not self.search_trace
            and self.coverage is not Coverage.none
        ):
            raise ValueError(
                f"{INVARIANT_PREFIX} no_evidence without search_trace requires coverage none"
            )

    def to_dict(self) -> dict:
        return {
            "claim_id": self.claim_id,
            "status": _value(self.status),
            "confidence": _value(self.confidence),
            "locator": None if self.locator is None else self.locator.to_dict(),
            "coverage": _value(self.coverage),
            "evidence_ids": list(self.evidence_ids),
            "reason": self.reason,
            "search_trace": [p.to_dict() for p in self.search_trace],
            "rounds": self.rounds,
            "question": self.question,
            "question_priority": self.question_priority,
            "fix": self.fix,
        }