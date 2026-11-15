"""Streamlit 演示页面壳（C-DEMO@2）：三种输入源 + 「对账」按钮 + 报告正文。"""

from __future__ import annotations

import tempfile
from pathlib import Path

import streamlit as st

if __package__:
    from .report import build
    from .source import clone_github, extract_zip
else:  # streamlit run 以脚本方式执行本文件
    from report import build
    from source import clone_github, extract_zip

TITLE = "对账引擎"
MODE_LABEL = "输入方式"
INPUT_MODES = ("服务器路径", "上传 zip", "GitHub URL")
MODE_PATH = INPUT_MODES[0]
MODE_ZIP = INPUT_MODES[1]
MODE_URL = INPUT_MODES[2]
REPO_LABEL = "仓库路径"
ZIP_LABEL = "仓库 zip 包"
URL_LABEL = "GitHub 仓库 URL"
SPEC_LABEL = "需求清单（可选，留空则用仓库 README 的自我声称）"
RUN_LABEL = "对账"


def _locate_repo(
    mode: str,
    repo_dir: str,
    upload,
    repo_url: str,
    workdir: Path,
) -> Path:
    """把所选输入源落到 ``workdir`` 内，返回待对账的仓库目录。"""
    if mode == MODE_PATH:
        path = repo_dir.strip()
        if not path:
            raise ValueError("请填写服务器上的仓库路径")
        return Path(path)

    if mode == MODE_ZIP:
        if upload is None:
            raise ValueError("请先选择一个 zip 文件再点击「对账」")
        dest = workdir / "upload"
        dest.mkdir()
        return extract_zip(upload.getvalue(), dest)

    url = repo_url.strip()
    if not url:
        raise ValueError("请填写 GitHub 仓库 URL（https://github.com/<owner>/<repo>）")
    dest = workdir / "clone"
    dest.mkdir()
    return clone_github(url, dest)


def main() -> None:
    st.title(TITLE)
    mode = st.radio(MODE_LABEL, INPUT_MODES)
    repo_dir = ""
    repo_url = ""
    upload = None
    if mode == MODE_PATH:
        repo_dir = st.text_input(REPO_LABEL)
    elif mode == MODE_ZIP:
        upload = st.file_uploader(ZIP_LABEL, type=["zip"])
    else:
        repo_url = st.text_input(URL_LABEL)
    spec_path = st.text_input(SPEC_LABEL)

    if not st.button(RUN_LABEL):
        return

    try:
        with tempfile.TemporaryDirectory() as workdir:
            repo = _locate_repo(mode, repo_dir, upload, repo_url, Path(workdir))
            report = build(repo, spec_path or None)
    except (OSError, ValueError) as exc:
        st.error(str(exc))
        return

    st.markdown(report)


if __name__ == "__main__":
    main()