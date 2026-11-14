"""演示层测试（C-DEMO@1 / 验收不变量 A4）。

``demo/report.py`` 不依赖 streamlit，因此这些用例在无 streamlit 环境也能跑。
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from demo import report as demo_report

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "contract" / "fixtures"
REPORTS = ROOT / "reports"
FX_CONTRADICTED = FIXTURES / "fx-contradicted"
APP_SOURCE = ROOT / "demo" / "app.py"


def _imported_roots(source: str) -> set[str]:
    roots: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            roots.add(node.module.split(".")[0])
    return roots


def _st_calls(tree: ast.Module, attr: str) -> list[ast.Call]:
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == attr
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "st"
    ]


def _string_constants(tree: ast.Module) -> set[str]:
    return {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }


def test_build_matches_snapshot_verbatim() -> None:
    spec = FX_CONTRADICTED / "requirements.md"
    expected = (REPORTS / "fx-contradicted.md").read_text(encoding="utf-8")

    assert demo_report.build(FX_CONTRADICTED, spec) == expected


def test_build_without_spec_uses_claims_path() -> None:
    text = demo_report.build(FX_CONTRADICTED)

    assert text.startswith("# fx-contradicted 对账报告")
    assert "## 概览" in text


def test_build_does_not_write_into_cwd(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    demo_report.build(FX_CONTRADICTED, FX_CONTRADICTED / "requirements.md")

    assert list(tmp_path.iterdir()) == []


def test_missing_repo_raises_oserror(tmp_path: Path) -> None:
    with pytest.raises(OSError):
        demo_report.build(tmp_path / "absent")


def test_missing_spec_raises_oserror() -> None:
    with pytest.raises(OSError):
        demo_report.build(FX_CONTRADICTED, FX_CONTRADICTED / "absent.md")


def test_report_module_does_not_import_streamlit() -> None:
    source = Path(demo_report.__file__).read_text(encoding="utf-8")

    assert "streamlit" not in _imported_roots(source)


def test_app_is_streamlit_shell() -> None:
    tree = ast.parse(APP_SOURCE.read_text(encoding="utf-8"))
    constants = _string_constants(tree)

    assert _st_calls(tree, "title"), "缺少 st.title(...) 调用"
    assert "对账引擎" in constants
    assert len(_st_calls(tree, "text_input")) == 2
    assert "仓库路径" in constants
    assert "需求清单（可选，留空则用仓库 README 的自我声称）" in constants
    assert _st_calls(tree, "button"), '缺少 st.button("对账") 调用'
    assert "对账" in constants
    assert _st_calls(tree, "markdown"), "缺少 st.markdown(...) 调用"


def test_app_catches_only_oserror_and_valueerror() -> None:
    source = APP_SOURCE.read_text(encoding="utf-8")

    assert "except (OSError, ValueError) as exc" in source
    assert "except Exception" not in source