"""命令行入口：``gap analyze`` / ``gap questions`` / ``gap spec`` / ``gap score``
（C-CLI@1 / C-CLI@2 / C-CLI@3 / C-CLI@4），以及 ``gap parse-spec`` / ``gap advise``
（C-LLM@1/cli）。
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from pathlib import Path

from .advice import render_advice
from .llm import LlmProvider, load_provider
from .metrics import compute
from .pipeline import analyze_repo, analyze_spec, render_spec_to, render_to
from .priority import sort_key, weight_breakdown
from .progress import resolve_progress
from .review import RECEIPT_KEYS, load_receipts, score
from .schema import (
    Claim,
    ClaimType,
    Confidence,
    Coverage,
    Locator,
    SearchProbe,
    Status,
    Verdict,
)
from .spec import parse_spec
from .specjson import write_spec_json

DEFAULT_OUT = "reports/report.md"
DEFAULT_SPEC_OUT_DIR = "reports"
SPEC_EMPTY_MESSAGE = '需求清单里没有找到条目（请用 "- " 或 "1. " 开头）'
LLM_DEGRADED_MESSAGE = "未配置 GAP_LLM_API_KEY，已降级为规则解析"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="gap", description="代码能力对账引擎")
    sub = parser.add_subparsers(dest="command")

    analyze = sub.add_parser("analyze", help="分析仓库并生成报告")
    analyze.add_argument("repo")
    analyze.add_argument("--out", default=DEFAULT_OUT)
    analyze.add_argument("--max-claims", type=int, default=5)
    analyze.add_argument("--json", default=None)

    questions = sub.add_parser("questions", help="按优先级列出会被问到的问题")
    questions.add_argument("repo")
    questions.add_argument("--spec", default=None)
    questions.add_argument("--top", type=int, default=5)
    questions.add_argument("--json", default=None)

    spec = sub.add_parser("spec", help="按需求清单对账仓库")
    spec.add_argument("repo")
    spec.add_argument("--spec", required=True)
    spec.add_argument("--out", default=None)

    score_parser = sub.add_parser("score", help="按回执计算七指标")
    score_parser.add_argument("--analysis", required=True)
    score_parser.add_argument("--receipts", default=None)
    score_parser.add_argument("--out", default=None)
    score_parser.add_argument("--json", default=None)

    parse_spec_parser = sub.add_parser(
        "parse-spec", help="把需求清单固化为 gap-spec@1 JSON"
    )
    parse_spec_parser.add_argument("spec")
    parse_spec_parser.add_argument("--out", required=True)
    parse_spec_parser.add_argument("--llm", action="store_true")
    _add_progress_flag(parse_spec_parser)

    advise_parser = sub.add_parser(
        "advise", help="为没找到证据的条目生成 AI 推演建议（独立产物）"
    )
    advise_parser.add_argument("repo")
    advise_parser.add_argument("--spec", required=True)
    advise_parser.add_argument("--out", required=True)
    advise_parser.add_argument("--llm", action="store_true")
    _add_progress_flag(advise_parser)

    return parser


def _add_progress_flag(parser: argparse.ArgumentParser) -> None:
    """三态开关：None 按 stderr 是否交互终端自动判定。"""
    parser.add_argument(
        "--progress",
        action=argparse.BooleanOptionalAction,
        dest="progress",
        default=None,
        help="在 stderr 显示逐条模型调用进度（默认仅交互终端显示）",
    )


def _provider_for(use_llm: bool, message: str) -> LlmProvider | None:
    """``--llm`` 未开启时绝不探测环境、绝不发起调用（R8）。"""
    if not use_llm:
        return None
    provider = load_provider()
    if provider is None:
        print(message, file=sys.stderr)
    return provider


def _read_spec_text(spec_arg: str) -> str | None:
    try:
        return Path(spec_arg).read_text(encoding="utf-8", errors="replace")
    except OSError:
        print(f"spec 文件不存在：{spec_arg}", file=sys.stderr)
        return None


def _missing_repo(repo: str) -> bool:
    if Path(repo).exists():
        return False
    print(f"error: 仓库路径不存在: {repo}", file=sys.stderr)
    return True


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def analyze(args: argparse.Namespace) -> int:
    if _missing_repo(args.repo):
        return 1

    repo = Path(args.repo)
    claims, verdicts = analyze_repo(repo, max_claims=args.max_claims)
    path = render_to(repo, Path(args.out), claims=claims, verdicts=verdicts)
    print(f"report: {path}")

    if args.json:
        payload = {
            "claims": [claim.to_dict() for claim in claims],
            "verdicts": [verdict.to_dict() for verdict in verdicts],
            "metrics": compute(claims, verdicts),
        }
        json_path = Path(args.json)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    return 0


def questions(args: argparse.Namespace) -> int:
    if _missing_repo(args.repo):
        return 1

    repo = Path(args.repo)
    if args.spec:
        spec_path = Path(args.spec)
        try:
            text = spec_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            print(f"spec 文件不存在：{args.spec}", file=sys.stderr)
            return 2

        if not parse_spec(text):
            print(SPEC_EMPTY_MESSAGE, file=sys.stderr)
            return 2

        analysis = analyze_spec(repo, text, spec_path=spec_path.name)
        claims, verdicts = analysis.claims, analysis.verdicts
    else:
        claims, verdicts = analyze_repo(repo)

    claim_by_id = {claim.id: claim for claim in claims}
    ordered = sorted(verdicts, key=sort_key)[: max(1, args.top)]

    rows: list[dict[str, object]] = []
    for verdict in ordered:
        claim = claim_by_id.get(verdict.claim_id)
        if claim is None:
            continue
        status_weight, gap_weight = weight_breakdown(verdict.status, verdict.confidence)
        print(
            f"[{verdict.question_priority}] {claim.text} → {verdict.question}"
            f"（状态 {verdict.status.value} +{status_weight}，"
            f"缺口 {verdict.confidence.value} +{gap_weight}）"
        )
        rows.append(
            {
                "claim_id": verdict.claim_id,
                "text": claim.text,
                "question": verdict.question,
                "question_priority": verdict.question_priority,
                "status_weight": status_weight,
                "gap_weight": gap_weight,
                "status": verdict.status.value,
                "confidence": verdict.confidence.value,
            }
        )

    if args.json:
        _write_json(Path(args.json), {"questions": rows, "total": len(rows)})

    return 0


def spec_command(args: argparse.Namespace) -> int:
    if _missing_repo(args.repo):
        return 1

    spec_path = Path(args.spec)
    try:
        text = spec_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        print(f"spec 文件不存在：{args.spec}", file=sys.stderr)
        return 2

    if not parse_spec(text):
        print(SPEC_EMPTY_MESSAGE, file=sys.stderr)
        return 2

    repo = Path(args.repo)
    out = Path(args.out) if args.out else Path(DEFAULT_SPEC_OUT_DIR) / f"{repo.name}-spec.md"
    path = render_spec_to(repo, spec_path, out)
    print(f"report: {path}")
    return 0


def parse_spec_command(args: argparse.Namespace) -> int:
    text = _read_spec_text(args.spec)
    if text is None:
        return 2
    if not parse_spec(text):
        print(SPEC_EMPTY_MESSAGE, file=sys.stderr)
        return 2

    provider = _provider_for(args.llm, LLM_DEGRADED_MESSAGE)
    progress = resolve_progress(args.progress, sys.stderr)
    path = write_spec_json(
        text, Path(args.spec).name, Path(args.out), provider, progress=progress
    )
    print(f"spec: {path}")
    return 0


def advise_command(args: argparse.Namespace) -> int:
    if _missing_repo(args.repo):
        return 1

    text = _read_spec_text(args.spec)
    if text is None:
        return 2
    if not parse_spec(text):
        print(SPEC_EMPTY_MESSAGE, file=sys.stderr)
        return 2

    provider = _provider_for(args.llm, LLM_DEGRADED_MESSAGE)
    progress = resolve_progress(args.progress, sys.stderr)
    analysis = analyze_spec(Path(args.repo), text, spec_path=Path(args.spec).name)
    path = render_advice(analysis, Path(args.out), provider, progress=progress)
    print(f"advice: {path}")
    return 0


def _pct(value: int | float) -> str:
    return f"{round(value * 100, 1):.1f}"


def _score_lines(result: dict[str, int | float]) -> list[str]:
    n_agree = int(result["n_agree"])
    n_disagree = int(result["n_disagree"])
    n_asserted = int(result["n_asserted"])
    n_silent = int(result["n_silent"])
    n_valid = int(result["n_valid"])
    n_all_judgeable = int(result["n_all_judgeable"])
    return [
        f"需求提出人认可率：{_pct(result['author_approval_rate'])}%"
        f"（N={n_agree + n_disagree}）",
        f"定位率：{_pct(result['locator_rate'])}%（N={n_asserted}）",
        f"漏报率（假阴性）：{_pct(result['false_negative_rate'])}%（N={n_silent}）",
        f"误报率（假阳性）：{_pct(result['false_positive_rate'])}%（N={n_asserted}）",
        f"无法证伪异议率：{_pct(result['unfalsifiable_rate'])}%（N={n_valid}）",
        f"说不清率：{_pct(result['unclear_rate'])}%（N={n_valid}）",
        f"未覆盖率：{_pct(result['uncovered_rate'])}%（N={n_all_judgeable}）",
    ]


def _parse_analysis(text: str) -> tuple[list[Claim], list[Verdict]]:
    payload = json.loads(text)
    claims = [
        Claim(
            id=item["id"],
            text=item["text"],
            source=item["source"],
            type=ClaimType(item["type"]),
            checkable=item.get("checkable", True),
            uncheckable_reason=item.get("uncheckable_reason"),
            out_of_scope=item.get("out_of_scope", False),
            authority=item.get("authority", "self"),
        )
        for item in payload["claims"]
    ]
    verdicts = [
        Verdict(
            claim_id=item["claim_id"],
            status=Status(item["status"]),
            confidence=Confidence(item["confidence"]),
            locator=None if item.get("locator") is None else Locator(**item["locator"]),
            coverage=Coverage(item["coverage"]),
            evidence_ids=list(item.get("evidence_ids", [])),
            reason=item.get("reason", ""),
            search_trace=[SearchProbe(**probe) for probe in item.get("search_trace", [])],
            rounds=item.get("rounds", 1),
            question=item.get("question", ""),
            question_priority=item.get("question_priority", 0),
            fix=item.get("fix", ""),
        )
        for item in payload["verdicts"]
    ]
    return claims, verdicts


def score_command(args: argparse.Namespace) -> int:
    analysis_path = Path(args.analysis)
    try:
        text = analysis_path.read_text(encoding="utf-8")
    except OSError:
        print(f"analysis 文件不存在：{args.analysis}", file=sys.stderr)
        return 2

    try:
        claims, verdicts = _parse_analysis(text)
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        print(f"analysis 文件格式错误：{args.analysis}", file=sys.stderr)
        return 2

    receipts = load_receipts(Path(args.receipts)) if args.receipts else []
    result = score(claims, verdicts, receipts)
    lines = _score_lines(result)
    for line in lines:
        print(line)

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        body = "# 指标（N 为分母）\n\n" + "\n".join(lines) + "\n"
        out_path.write_text(body, encoding="utf-8")

    if args.json:
        _write_json(Path(args.json), {key: result[key] for key in RECEIPT_KEYS})

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code or 0)

    handlers = {
        "analyze": analyze,
        "questions": questions,
        "spec": spec_command,
        "score": score_command,
        "parse-spec": parse_spec_command,
        "advise": advise_command,
    }
    handler = handlers.get(args.command or "")
    if handler is None:
        parser.print_usage(sys.stderr)
        return 2

    return handler(args)


if __name__ == "__main__":
    raise SystemExit(main())