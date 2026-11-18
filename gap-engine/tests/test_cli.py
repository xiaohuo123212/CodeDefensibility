"""CLI 子命令测试（C-CLI@2 / C-CLI@3）：三种退出码、报告落盘与问题分值拆解。"""

from __future__ import annotations

import json
import re
from pathlib import Path

from gap_engine import cli

SPEC_TEXT = "- 支持 Excel 导出\n"
QUESTION_LINE = re.compile(r"^\[\d+\] .+ → .+（状态 \w+ \+\d+，缺口 \w+ \+\d+）$")
QUESTION_KEYS = [
    "claim_id",
    "text",
    "question",
    "question_priority",
    "status_weight",
    "gap_weight",
    "status",
    "confidence",
]


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "app.py").write_text(
        "from flask import Flask\n"
        "\n"
        "app = Flask(__name__)\n"
        "\n"
        "\n"
        "@app.route('/export')\n"
        "def export():\n"
        "    import openpyxl\n"
        "    return 'ok'\n",
        encoding="utf-8",
    )
    (repo / "requirements.txt").write_text("flask\n", encoding="utf-8")
    return repo


def _spec(tmp_path: Path, text: str = SPEC_TEXT) -> Path:
    spec = tmp_path / "requirements.md"
    spec.write_text(text, encoding="utf-8")
    return spec


def test_analyze_report_contains_facts_section(tmp_path: Path, capsys) -> None:
    repo = _repo(tmp_path)
    out = tmp_path / "out" / "report.md"

    code = cli.main(["analyze", str(repo), "--out", str(out)])

    captured = capsys.readouterr()
    assert code == 0
    assert f"report: {out}" in captured.out
    text = out.read_text(encoding="utf-8")
    assert "## 项目实际是什么" in text
    assert "- 一句话：" in text
    assert "- 路由：1 个（GET /export）" in text
    assert text.index("## 项目实际是什么") < text.index("## 概览")


def test_spec_success_writes_report(tmp_path: Path, capsys) -> None:
    repo = _repo(tmp_path)
    spec = _spec(tmp_path)
    out = tmp_path / "out" / "repo-spec.md"

    code = cli.main(["spec", str(repo), "--spec", str(spec), "--out", str(out)])

    captured = capsys.readouterr()
    assert code == 0
    assert f"report: {out}" in captured.out
    assert captured.err == ""
    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert "# repo 需求对账报告" in text
    assert "## 需求可判定性预检" in text
    assert "## 项目实际是什么" in text


def test_spec_default_out_is_reports_dir(tmp_path: Path, monkeypatch, capsys) -> None:
    repo = _repo(tmp_path)
    spec = _spec(tmp_path)
    monkeypatch.chdir(tmp_path)

    code = cli.main(["spec", str(repo), "--spec", str(spec)])

    captured = capsys.readouterr()
    default_rel = Path("reports") / "repo-spec.md"
    assert code == 0
    assert f"report: {default_rel}" in captured.out
    assert (tmp_path / default_rel).exists()


def test_missing_spec_file_returns_two(tmp_path: Path, capsys) -> None:
    repo = _repo(tmp_path)
    missing = tmp_path / "absent.md"

    code = cli.main(["spec", str(repo), "--spec", str(missing)])

    captured = capsys.readouterr()
    assert code == 2
    assert f"spec 文件不存在：{missing}" in captured.err
    assert not (tmp_path / "reports").exists()


def test_empty_spec_returns_two_without_report(tmp_path: Path, capsys) -> None:
    repo = _repo(tmp_path)
    spec = _spec(tmp_path, "# 只有标题\n\n一段普通说明，没有列表条目。\n")
    out = tmp_path / "repo-spec.md"

    code = cli.main(["spec", str(repo), "--spec", str(spec), "--out", str(out)])

    captured = capsys.readouterr()
    assert code == 2
    assert "需求清单里没有找到条目" in captured.err
    assert not out.exists()


def test_missing_repo_returns_one(tmp_path: Path, capsys) -> None:
    spec = _spec(tmp_path)

    code = cli.main(["spec", str(tmp_path / "nope"), "--spec", str(spec)])

    captured = capsys.readouterr()
    assert code == 1
    assert "仓库路径不存在" in captured.err


def test_spec_argument_is_required(tmp_path: Path, capsys) -> None:
    code = cli.main(["spec", str(tmp_path)])

    captured = capsys.readouterr()
    assert code == 2
    assert "--spec" in captured.err


def _write_readme(repo: Path) -> None:
    (repo / "README.md").write_text(
        "- 支持 Excel 导出\n- 支持 CSV 导出\n", encoding="utf-8"
    )


def test_questions_spec_prints_breakdown_and_json(tmp_path: Path, capsys) -> None:
    repo = _repo(tmp_path)
    spec = _spec(tmp_path)
    out = tmp_path / "nested" / "questions.json"

    code = cli.main(
        [
            "questions",
            str(repo),
            "--spec",
            str(spec),
            "--top",
            "2",
            "--json",
            str(out),
        ]
    )

    captured = capsys.readouterr()
    assert code == 0
    assert captured.err == ""
    lines = captured.out.splitlines()
    assert lines
    assert all(QUESTION_LINE.match(line) for line in lines)

    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["total"] == len(lines) == len(payload["questions"])
    for row in payload["questions"]:
        assert list(row) == QUESTION_KEYS
        assert row["status_weight"] + row["gap_weight"] >= 2


def test_questions_readme_mode_is_idempotent(tmp_path: Path, capsys) -> None:
    repo = _repo(tmp_path)
    _write_readme(repo)

    first = cli.main(["questions", str(repo)])
    first_out = capsys.readouterr()
    second = cli.main(["questions", str(repo)])
    second_out = capsys.readouterr()

    assert first == 0 and second == 0
    assert first_out.out == second_out.out
    lines = first_out.out.splitlines()
    assert lines
    assert all(QUESTION_LINE.match(line) for line in lines)


def test_questions_top_is_clamped_to_at_least_one(tmp_path: Path, capsys) -> None:
    repo = _repo(tmp_path)
    spec = _spec(tmp_path)

    for top in ("0", "-3"):
        code = cli.main(
            ["questions", str(repo), "--spec", str(spec), "--top", top]
        )
        captured = capsys.readouterr()
        assert code == 0
        assert len(captured.out.splitlines()) == 1


def test_questions_missing_spec_returns_two(tmp_path: Path, capsys) -> None:
    repo = _repo(tmp_path)
    missing = tmp_path / "absent.md"

    code = cli.main(["questions", str(repo), "--spec", str(missing)])

    captured = capsys.readouterr()
    assert code == 2
    assert f"spec 文件不存在：{missing}" in captured.err


def test_questions_empty_spec_returns_two(tmp_path: Path, capsys) -> None:
    repo = _repo(tmp_path)
    spec = _spec(tmp_path, "# 只有标题\n\n一段普通说明，没有列表条目。\n")

    code = cli.main(["questions", str(repo), "--spec", str(spec)])

    captured = capsys.readouterr()
    assert code == 2
    assert "需求清单里没有找到条目" in captured.err


def test_questions_missing_repo_returns_one(tmp_path: Path, capsys) -> None:
    spec = _spec(tmp_path)

    code = cli.main(["questions", str(tmp_path / "nope"), "--spec", str(spec)])

    captured = capsys.readouterr()
    assert code == 1
    assert "仓库路径不存在" in captured.err


def test_unknown_command_returns_two(capsys) -> None:
    code = cli.main([])

    captured = capsys.readouterr()
    assert code == 2
    assert "usage" in captured.err

def test_overview_entry_line_ignores_non_route_entry_evidence(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "script.py").write_text(
        'import sys\n\n\nif __name__ == "__main__":\n    sys.exit(0)\n', encoding="utf-8"
    )
    out = tmp_path / "out" / "repo-spec.md"

    assert cli.main(["spec", str(repo), "--spec", str(_spec(tmp_path)), "--out", str(out)]) == 0
    text = out.read_text(encoding="utf-8")

    assert "- 入口：未识别到启动入口" in text
    assert "- 一句话：未识别到启动入口；" in text


def test_overview_entry_line_lists_route_files(tmp_path: Path) -> None:
    out = tmp_path / "out" / "repo-spec.md"

    assert cli.main(["spec", str(_repo(tmp_path)), "--spec", str(_spec(tmp_path)), "--out", str(out)]) == 0
    text = out.read_text(encoding="utf-8")

    assert "- 入口：app.py" in text
    assert "- 一句话：app.py 暴露 1 个路由；" in text

def test_spec_marks_out_of_scope_requirement_as_not_judged(tmp_path: Path) -> None:
    spec = _spec(tmp_path, "- 支持 VS Code 编辑器插件\n- 支持导出\n")
    out = tmp_path / "out" / "repo-spec.md"

    assert cli.main(["spec", str(_repo(tmp_path)), "--spec", str(spec), "--out", str(out)]) == 0
    text = out.read_text(encoding="utf-8")

    assert "结论：不判定（超出判定域" in text
    assert "- 其中 1 条超出判定域，不判定" in text
    assert "支持 VS Code 编辑器插件：没有找到任何可查痕迹" not in text
    assert "audit effort：0 类 0 处" in text