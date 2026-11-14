"""Streamlit 演示页面壳（C-DEMO@1）：两个输入框 + 「对账」按钮 + 报告正文。"""

from __future__ import annotations

import streamlit as st

if __package__:
    from .report import build
else:  # streamlit run 以脚本方式执行本文件
    from report import build

TITLE = "对账引擎"
REPO_LABEL = "仓库路径"
SPEC_LABEL = "需求清单（可选，留空则用仓库 README 的自我声称）"


def main() -> None:
    st.title(TITLE)
    repo_dir = st.text_input(REPO_LABEL)
    spec_path = st.text_input(SPEC_LABEL)

    if not st.button("对账"):
        return

    try:
        report = build(repo_dir, spec_path or None)
    except (OSError, ValueError) as exc:
        st.error(str(exc))
        return

    st.markdown(report)


if __name__ == "__main__":
    main()