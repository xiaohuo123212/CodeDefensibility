"""回执七指标与 ``gap score``（C-REVIEW@1 / C-CLI@4）。"""

from __future__ import annotations

import json
from pathlib import Path

from gap_engine import cli
from gap_engine.review import RECEIPT_KEYS, Receipt, load_receipts, score
from gap_engine.schema import (
    Claim,
    ClaimType,
    Confidence,
    Coverage,
    Locator,
    SearchProbe,
    Status,
    Verdict,
)

EXPECTED_KEYS = (
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

EXPECTED_LINES = [
    "需求提出人认可率：25.0%（N=4）",
    "定位率：100.0%（N=2）",
    "漏报率（假阴性）：33.3%（N=3）",
    "误报率（假阳性）：50.0%（N=2）",
    "无法证伪异议率：20.0%（N=5）",
    "说不清率：20.0%（N=5）",
    "未覆盖率：66.7%（N=3）",
]


def _claim(
    cid: str, ctype: ClaimType = ClaimType.feature, out_of_scope: bool = False
) -> Claim:
    return Claim(
        id=cid,
        text=f"声称 {cid}",
        source="readme",
        type=ctype,
        out_of_scope=out_of_scope,
    )


def _verdict(
    cid: str,
    status: Status,
    coverage: Coverage,
    locator: Locator | None = None,
    search_trace: list[SearchProbe] | None = None,
) -> Verdict:
    return Verdict(
        claim_id=cid,
        status=status,
        confidence=Confidence.high,
        locator=locator,
        coverage=coverage,
        evidence_ids=[],
        reason="",
        search_trace=search_trace or [],
    )


def _fixtures() -> tuple[list[Claim], list[Verdict], list[Receipt]]:
    claims = [
        _claim("c1"),
        _claim("c2", ClaimType.performance),
        _claim("c3", ClaimType.security),
        _claim("c4", out_of_scope=True),
        _claim("c5", ClaimType.testing),
    ]
    verdicts = [
        _verdict("c1", Status.supported, Coverage.full, Locator(file="app.py", line=1)),
        _verdict("c2", Status.no_evidence, Coverage.none),
        _verdict("c3", Status.no_evidence, Coverage.none),
        _verdict("c4", Status.supported, Coverage.full, Locator(file="app.py", line=2)),
        _verdict(
            "c5",
            Status.no_evidence,
            Coverage.partial,
            search_trace=[
                SearchProbe(probe="p", target="t", scanned=1, hits=0, where=[])
            ],
        ),
    ]
    receipts = [
        Receipt("c1", "对"),
        Receipt("c1", "错", "app.py:10"),
        Receipt("c5", "错"),
        Receipt("c5", "错", "app.py:5"),
        Receipt("c2", "对"),
        Receipt("c3", "对"),
        Receipt("c4", "对"),
        Receipt("c99", "对"),
        Receipt("c5", "说不清"),
    ]
    return claims, verdicts, receipts


def test_receipt_keys_are_fixed_and_ordered() -> None:
    assert len(RECEIPT_KEYS) == 20
    assert RECEIPT_KEYS == EXPECTED_KEYS


def test_score_counts_and_rates() -> None:
    claims, verdicts, receipts = _fixtures()

    result = score(claims, verdicts, receipts)

    assert list(result) == list(RECEIPT_KEYS)
    assert result == {
        "n_receipts": 9,
        "n_valid": 5,
        "n_agree": 1,
        "n_disagree": 3,
        "n_unclear": 1,
        "n_falsifiable_dispute": 1,
        "n_asserted": 2,
        "n_asserted_located": 2,
        "n_silent": 3,
        "n_fn": 1,
        "n_fp": 1,
        "n_all_output": 2,
        "n_all_judgeable": 3,
        "author_approval_rate": 0.25,
        "locator_rate": 1.0,
        "false_negative_rate": 0.3333,
        "false_positive_rate": 0.5,
        "unfalsifiable_rate": 0.2,
        "unclear_rate": 0.2,
        "uncovered_rate": 0.6667,
    }


def test_score_zero_denominators_yield_zero_rates() -> None:
    result = score([], [], [])

    assert result["n_receipts"] == 0
    assert result["n_valid"] == 0
    for key in (
        "author_approval_rate",
        "locator_rate",
        "false_negative_rate",
        "false_positive_rate",
        "unfalsifiable_rate",
        "unclear_rate",
        "uncovered_rate",
    ):
        assert result[key] == 0.0


def test_load_receipts_skips_invalid_lines(tmp_path: Path) -> None:
    path = tmp_path / "receipts.jsonl"
    path.write_text(
        "\n"
        '{"claim_id": "c1", "author_verdict": "对"}\n'
        "{not json}\n"
        '{"author_verdict": "对"}\n'
        '{"claim_id": "c2", "author_verdict": "存疑"}\n'
        '{"claim_id": "c3", "author_verdict": "错", "author_evidence": "app.py:7"}\n'
        '["c4"]\n'
        '{"claim_id": "c5", "author_verdict": "说不清"}\n',
        encoding="utf-8",
    )

    assert load_receipts(path) == [
        Receipt("c1", "对"),
        Receipt("c3", "错", "app.py:7"),
        Receipt("c5", "说不清"),
    ]


def test_load_receipts_missing_file_returns_empty(tmp_path: Path) -> None:
    assert load_receipts(tmp_path / "absent.jsonl") == []


def _write_analysis(tmp_path: Path) -> Path:
    claims, verdicts, _ = _fixtures()
    path = tmp_path / "analysis.json"
    path.write_text(
        json.dumps(
            {
                "claims": [claim.to_dict() for claim in claims],
                "verdicts": [verdict.to_dict() for verdict in verdicts],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return path


def _write_receipts(tmp_path: Path) -> Path:
    _, _, receipts = _fixtures()
    path = tmp_path / "receipts.jsonl"
    path.write_text(
        "".join(
            json.dumps(
                {
                    "claim_id": receipt.claim_id,
                    "author_verdict": receipt.verdict,
                    "author_evidence": receipt.evidence,
                },
                ensure_ascii=False,
            )
            + "\n"
            for receipt in receipts
        ),
        encoding="utf-8",
    )
    return path


def test_score_cli_prints_seven_lines_and_writes_files(tmp_path: Path, capsys) -> None:
    analysis = _write_analysis(tmp_path)
    receipts = _write_receipts(tmp_path)
    out = tmp_path / "out" / "score.md"
    json_path = tmp_path / "out" / "score.json"

    code = cli.main(
        [
            "score",
            "--analysis",
            str(analysis),
            "--receipts",
            str(receipts),
            "--out",
            str(out),
            "--json",
            str(json_path),
        ]
    )

    captured = capsys.readouterr()
    assert code == 0
    assert captured.err == ""
    assert captured.out.splitlines() == EXPECTED_LINES
    assert out.read_text(encoding="utf-8") == (
        "# 指标（N 为分母）\n\n" + "\n".join(EXPECTED_LINES) + "\n"
    )

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert list(payload) == list(RECEIPT_KEYS)
    assert payload == score(*_fixtures())


def test_score_cli_without_receipts_prints_zeros(tmp_path: Path, capsys) -> None:
    analysis = _write_analysis(tmp_path)

    code = cli.main(["score", "--analysis", str(analysis)])

    captured = capsys.readouterr()
    lines = captured.out.splitlines()
    assert code == 0
    assert len(lines) == 7
    assert lines[0] == "需求提出人认可率：0.0%（N=0）"
    assert lines[6] == "未覆盖率：66.7%（N=3）"


def test_score_cli_missing_analysis_returns_two(tmp_path: Path, capsys) -> None:
    missing = tmp_path / "absent.json"

    code = cli.main(["score", "--analysis", str(missing)])

    captured = capsys.readouterr()
    assert code == 2
    assert f"analysis 文件不存在：{missing}" in captured.err


def test_score_cli_bad_analysis_returns_two(tmp_path: Path, capsys) -> None:
    path = tmp_path / "bad.json"
    path.write_text("{not json", encoding="utf-8")

    code = cli.main(["score", "--analysis", str(path)])

    captured = capsys.readouterr()
    assert code == 2
    assert f"analysis 文件格式错误：{path}" in captured.err