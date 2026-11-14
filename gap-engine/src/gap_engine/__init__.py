"""gap_engine —— 对账引擎契约内核。

对外唯一交换格式与判定纪律见 ``contract/CONTRACT.md``。
"""

from .matcher import (
    FIX_TEMPLATES,
    LOCAL_COMPLETION_PROMPT,
    QUESTION_TEMPLATES,
    fix,
    gap_label,
    judge,
    question,
)
from .metrics import METRIC_KEYS, compute
from .pipeline import analyze_repo, render_to
from .priority import (
    CONFIDENCE_WEIGHT,
    STATUS_WEIGHT,
    compute_question_priority,
    sort_key,
)
from .renderer import STATUS_CN, render
from .schema import (
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
from .trace import TraceSummary, headline, summarize

__version__ = "0.1.0"

__all__ = [
    "CONFIDENCE_WEIGHT",
    "FIX_TEMPLATES",
    "JUDGEABLE_TYPES",
    "LOCAL_COMPLETION_PROMPT",
    "METRIC_KEYS",
    "QUESTION_TEMPLATES",
    "STATUS_CN",
    "STATUS_WEIGHT",
    "Claim",
    "ClaimType",
    "Confidence",
    "Coverage",
    "Evidence",
    "EvidenceKind",
    "Locator",
    "SearchProbe",
    "Status",
    "Strength",
    "TraceSummary",
    "Verdict",
    "analyze_repo",
    "compute",
    "compute_question_priority",
    "fix",
    "gap_label",
    "headline",
    "is_judgeable",
    "judge",
    "question",
    "render",
    "render_to",
    "sort_key",
    "summarize",
]