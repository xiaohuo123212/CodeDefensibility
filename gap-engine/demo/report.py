"""演示层：仓库（+ 需求清单）→ 报告正文（C-DEMO@1）。

渲染一律复用 ``gap_engine.pipeline`` 的入口，演示层不参与任何文案加工，
因此同一输入的输出与 CLI 落盘的报告逐字一致。本模块不依赖 streamlit。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from gap_engine.pipeline import render_spec_to, render_to


def build(repo_dir: str | Path, spec_path: str | Path | None = None) -> str:
    repo = Path(repo_dir)
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "report.md"
        if spec_path is None:
            render_to(repo, out)
        else:
            render_spec_to(repo, Path(spec_path), out)
        return out.read_text(encoding="utf-8")