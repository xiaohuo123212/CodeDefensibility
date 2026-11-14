"""C-PREVALENCE@1：多份 analysis 聚合、JSON 结构与 load_prevalence 兼容性。"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from gap_engine.baseline import PREVALENCE, load_prevalence
from gap_engine.schema import ClaimType

TOOLS = Path(__file__).resolve().parents[1] / "tools"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "measure_prevalence", TOOLS / "measure_prevalence.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


measure_prevalence = _load_module()

A_CLAIMS = [
    {"id": "c01", "type": "performance", "out_of_scope": False},
    {"id": "c02", "type": "performance", "out_of_scope": False},
    {"id": "c03", "type": "testing", "out_of_scope": False},
    {"id": "c04", "type": "feature", "out_of_scope": True},
    {"id": "c05", "type": "architecture", "out_of_scope": False},
]
A_VERDICTS = [
    {"claim_id": "c01", "status": "supported"},
    {"claim_id": "c02", "status": "no_evidence"},
    {"claim_id": "c03", "status": "contradicted"},
    {"claim_id": "c04", "status": "supported"},
    {"claim_id": "c05", "status": "supported"},
]
B_CLAIMS = [
    {"id": "c01", "type": "performance", "out_of_scope": False},
    {"id": "c02", "type": "feature", "out_of_scope": False},
    {"id": "c03", "type": "feature", "out_of_scope": False},
]
B_VERDICTS = [
    {"claim_id": "c01", "status": "contradicted"},
    {"claim_id": "c02", "status": "supported"},
    {"claim_id": "c03", "status": "no_evidence"},
]


def _write_analysis(path: Path, claims: list[dict], verdicts: list[dict]) -> Path:
    payload = {"claims": claims, "verdicts": verdicts, "metrics": {}}
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


@pytest.fixture()
def analysis_files(tmp_path: Path) -> tuple[Path, Path]:
    return (
        _write_analysis(tmp_path / "a.json", A_CLAIMS, A_VERDICTS),
        _write_analysis(tmp_path / "b.json", B_CLAIMS, B_VERDICTS),
    )


def test_measure_aggregates_judgeable_in_scope_claims(analysis_files: tuple[Path, Path]) -> None:
    result = measure_prevalence.measure(list(analysis_files))

    assert result["performance"] == {"n_claims": 3, "n_prevalent": 2, "prevalence": 0.6667}
    assert result["testing"] == {"n_claims": 1, "n_prevalent": 1, "prevalence": 1.0}
    assert result["feature"] == {"n_claims": 2, "n_prevalent": 1, "prevalence": 0.5}
    assert result["_source"] == "measured"
    assert result["_n_projects"] == 2


def test_measure_keeps_all_seven_types_with_zero_prevalence(
    analysis_files: tuple[Path, Path],
) -> None:
    result = measure_prevalence.measure(list(analysis_files))

    assert set(ClaimType.__members__) <= set(result)
    for name in ("concurrency", "architecture", "scale", "security"):
        assert result[name] == {"n_claims": 0, "n_prevalent": 0, "prevalence": 0.0}


def test_main_writes_json_with_seven_types_and_metadata(
    analysis_files: tuple[Path, Path], tmp_path: Path
) -> None:
    a, b = analysis_files
    out = tmp_path / "reports" / "prevalence.json"
    assert measure_prevalence.main(["--analysis", str(a), str(b), "--out", str(out)]) == 0

    raw = json.loads(out.read_text(encoding="utf-8"))
    for claim_type in ClaimType:
        row = raw[claim_type.value]
        assert set(row) == {"n_claims", "n_prevalent", "prevalence"}
    assert raw["_source"] == "measured"
    assert raw["_n_projects"] == 2


def test_compare_prints_one_row_per_type(
    analysis_files: tuple[Path, Path], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    a, b = analysis_files
    out = tmp_path / "prevalence.json"
    code = measure_prevalence.main(["--analysis", str(a), str(b), "--out", str(out), "--compare"])

    assert code == 0
    lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]
    assert len(lines) == 7
    assert lines[0] == f"performance：实测 66.7%（N=3）｜先验 {PREVALENCE[ClaimType.performance] * 100:.0f}%"
    assert "实测" in lines[6] and "先验" in lines[6]


def test_missing_analysis_file_returns_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out = tmp_path / "prevalence.json"
    code = measure_prevalence.main(["--analysis", str(tmp_path / "nope.json"), "--out", str(out)])

    assert code == 2
    assert "nope.json" in capsys.readouterr().err
    assert not out.exists()


def test_broken_json_returns_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    broken = tmp_path / "broken.json"
    broken.write_text("{not json", encoding="utf-8")
    out = tmp_path / "prevalence.json"
    code = measure_prevalence.main(["--analysis", str(broken), "--out", str(out)])

    assert code == 2
    assert "broken.json" in capsys.readouterr().err


def test_load_prevalence_accepts_written_file(
    analysis_files: tuple[Path, Path], tmp_path: Path
) -> None:
    a, b = analysis_files
    out = tmp_path / "prevalence.json"
    assert measure_prevalence.main(["--analysis", str(a), str(b), "--out", str(out)]) == 0

    table = load_prevalence(out)
    assert set(table) == set(ClaimType)



def test_load_prevalence_reads_back_measured_values(
    analysis_files: tuple[Path, Path], tmp_path: Path
) -> None:
    a, b = analysis_files
    out = tmp_path / "prevalence.json"
    assert measure_prevalence.main(["--analysis", str(a), str(b), "--out", str(out)]) == 0

    table = load_prevalence(out)
    assert table[ClaimType.performance] == pytest.approx(0.6667)
    assert table[ClaimType.feature] == pytest.approx(0.5)

def test_load_prevalence_accepts_flat_legacy_file(tmp_path: Path) -> None:
    path = tmp_path / "prevalence.json"
    path.write_text('{"performance": 0.9, "testing": 0.75}', encoding="utf-8")

    table = load_prevalence(path)
    assert set(table) == set(ClaimType)
    assert table[ClaimType.performance] == pytest.approx(0.9)
    assert table[ClaimType.testing] == pytest.approx(0.75)
    assert table[ClaimType.feature] == PREVALENCE[ClaimType.feature]