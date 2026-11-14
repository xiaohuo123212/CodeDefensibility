"""命令行入口：``gap analyze`` / ``gap questions`` / ``gap spec``（C-CLI@1 / C-CLI@2 / C-CLI@3）。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .metrics import compute
from .pipeline import analyze_repo, analyze_spec, render_spec_to, render_to
from .priority import sort_key, weight_breakdown
from .spec import parse_spec

DEFAULT_OUT = "reports/report.md"
DEFAULT_SPEC_OUT_DIR = "reports"
SPEC_EMPTY_MESSAGE = '需求清单里没有找到条目（请用 "- " 或 "1. " 开头）'


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

    return parser


def _missing_repo(repo: str) -> bool:
    if Path(repo).exists():
        return False
    print(f"error: 仓库路径不存在: {repo}", file=sys.stderr)
    return True


def _write_json(path: Path, payload: dict[str, object]) -> None:
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


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code or 0)

    handlers = {"analyze": analyze, "questions": questions, "spec": spec_command}
    handler = handlers.get(args.command or "")
    if handler is None:
        parser.print_usage(sys.stderr)
        return 2

    return handler(args)


if __name__ == "__main__":
    raise SystemExit(main())