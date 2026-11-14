"""把多份 ``gap analyze --json`` 产物聚合为实测普遍性（C-PREVALENCE@1）。

用法：
    python tools/measure_prevalence.py --analysis a.json [b.json ...] \
        --out reports/prevalence.json [--compare]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from gap_engine.baseline import PREVALENCE  # noqa: E402
from gap_engine.schema import ClaimType, Status, is_judgeable  # noqa: E402

PREVALENT_STATUSES: frozenset[str] = frozenset(
    {Status.supported.value, Status.contradicted.value}
)

EXIT_OK = 0
EXIT_INPUT_ERROR = 2


class AnalysisError(Exception):
    """输入 analysis 文件缺失或格式错误。"""


def _read_analysis(path: Path) -> dict:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise AnalysisError(f"无法读取 analysis 文件：{path}（{exc}）") from exc
    except ValueError as exc:
        raise AnalysisError(f"analysis 文件不是合法 JSON：{path}（{exc}）") from exc
    if not isinstance(raw, dict):
        raise AnalysisError(f"analysis 文件顶层必须是对象：{path}")
    return raw


def measure(paths: list[Path]) -> dict[str, object]:
    counts: dict[ClaimType, list[int]] = {claim_type: [0, 0] for claim_type in ClaimType}

    for path in paths:
        data = _read_analysis(path)
        claims = data.get("claims")
        verdicts = data.get("verdicts")
        if not isinstance(claims, list) or not isinstance(verdicts, list):
            raise AnalysisError(f"analysis 文件缺少 claims/verdicts 数组：{path}")

        statuses: dict[str, str] = {}
        for verdict in verdicts:
            if isinstance(verdict, dict):
                claim_id = verdict.get("claim_id")
                status = verdict.get("status")
                if isinstance(claim_id, str) and isinstance(status, str):
                    statuses[claim_id] = status

        for claim in claims:
            if not isinstance(claim, dict) or claim.get("out_of_scope"):
                continue
            try:
                claim_type = ClaimType(claim.get("type"))
            except ValueError:
                continue
            if not is_judgeable(claim_type):
                continue

            counts[claim_type][0] += 1
            claim_id = claim.get("id")
            if isinstance(claim_id, str) and statuses.get(claim_id) in PREVALENT_STATUSES:
                counts[claim_type][1] += 1

    result: dict[str, object] = {}
    for claim_type in ClaimType:
        n_claims, n_prevalent = counts[claim_type]
        result[claim_type.value] = {
            "n_claims": n_claims,
            "n_prevalent": n_prevalent,
            "prevalence": round(n_prevalent / n_claims, 4) if n_claims else 0.0,
        }
    result["_source"] = "measured"
    result["_n_projects"] = len(paths)
    return result


def _print_compare(result: dict[str, object]) -> None:
    for claim_type in ClaimType:
        row = result[claim_type.value]
        assert isinstance(row, dict)
        print(
            f"{claim_type.value}：实测 {row['prevalence'] * 100:.1f}%"
            f"（N={row['n_claims']}）｜先验 {PREVALENCE[claim_type] * 100:.0f}%"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="measure_prevalence")
    parser.add_argument("--analysis", nargs="+", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--compare", action="store_true")
    args = parser.parse_args(argv)

    try:
        result = measure(list(args.analysis))
    except AnalysisError as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_INPUT_ERROR

    try:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    except OSError as exc:
        print(f"无法写出 {args.out}（{exc}）", file=sys.stderr)
        return EXIT_INPUT_ERROR

    if args.compare:
        _print_compare(result)
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())