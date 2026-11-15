"""demo 输入源（C-DEMO@2）：受控 zip 解压与 GitHub 浅克隆。

只依赖标准库，禁止依赖 streamlit；供 ``demo/app.py`` 在临时目录内调用。
本模块不创建也不删除 ``dest``，清理责任归调用方。
"""

from __future__ import annotations

import io
import os
import re
import subprocess
import zipfile
from pathlib import Path

MAX_ZIP_BYTES = 20 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES = 200 * 1024 * 1024
MAX_FILES = 2000
CLONE_TIMEOUT = 120

_GITHUB_URL = re.compile(
    r"^https://github\.com/([A-Za-z0-9._-]+)/([A-Za-z0-9._-]+?)(\.git)?/?$"
)
_PATH_SEPARATORS = re.compile(r"[\\/]+")
_FILE_TYPE_MASK = 0o170000
_SYMLINK_TYPE = 0o120000
_CHUNK_BYTES = 64 * 1024
_STDERR_LIMIT = 200


def _segments(name: str) -> list[str]:
    return [part for part in _PATH_SEPARATORS.split(name) if part and part != "."]


def _validate_member(info: zipfile.ZipInfo) -> None:
    name = info.filename
    if not name:
        raise ValueError("zip 中存在空文件名成员")
    if name.startswith(("/", "\\")):
        raise ValueError(f"zip 成员是绝对路径，已拒绝：{name}")
    if (info.external_attr >> 16) & _FILE_TYPE_MASK == _SYMLINK_TYPE:
        raise ValueError(f"zip 成员是符号链接，已拒绝：{name}")

    segments = _segments(name)
    if not segments:
        raise ValueError(f"zip 成员名没有有效路径段，已拒绝：{name}")
    if ":" in segments[0]:
        raise ValueError(f"zip 成员含盘符，已拒绝：{name}")
    if ".." in segments:
        raise ValueError(f"zip 成员含上级目录引用，已拒绝：{name}")
    if Path(name).is_absolute():
        raise ValueError(f"zip 成员是绝对路径，已拒绝：{name}")


def _top_level(dest: Path) -> Path:
    entries = list(dest.iterdir())
    if len(entries) == 1 and entries[0].is_dir():
        return entries[0]
    return dest


def extract_zip(blob: bytes, dest: Path) -> Path:
    """把 ``blob`` 解压到已存在的 ``dest``，返回仓库根目录。"""
    if len(blob) > MAX_ZIP_BYTES:
        raise ValueError(
            f"上传体积 {len(blob)} 字节，超过上限 {MAX_ZIP_BYTES} 字节"
        )

    try:
        archive = zipfile.ZipFile(io.BytesIO(blob))
    except zipfile.BadZipFile as exc:
        raise ValueError(f"不是有效的 zip 文件：{exc}") from exc

    with archive:
        members = archive.infolist()
        for info in members:
            _validate_member(info)

        payloads = [info for info in members if not info.is_dir()]
        if len(payloads) > MAX_FILES:
            raise ValueError(
                f"zip 条目数 {len(payloads)} 超过上限 {MAX_FILES}"
            )

        extracted = 0
        for info in members:
            target = dest.joinpath(*_segments(info.filename))
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as src, target.open("wb") as out:
                while chunk := src.read(_CHUNK_BYTES):
                    extracted += len(chunk)
                    if extracted > MAX_UNCOMPRESSED_BYTES:
                        raise ValueError(
                            f"解压后累计体积超过上限 {MAX_UNCOMPRESSED_BYTES} 字节"
                        )
                    out.write(chunk)

    return _top_level(dest)


def clone_github(url: str, dest: Path) -> Path:
    """浅克隆 ``https://github.com/<owner>/<repo>`` 到空目录 ``dest``。"""
    if not _GITHUB_URL.match(url):
        raise ValueError(
            "只接受 https://github.com/<owner>/<repo> 形式的公开仓库地址，"
            f"已拒绝：{url}"
        )

    command = ["git", "clone", "--depth", "1", "--quiet", url, str(dest)]
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=CLONE_TIMEOUT,
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
        )
    except subprocess.TimeoutExpired as exc:
        raise TimeoutError(f"git clone 超时（{CLONE_TIMEOUT} 秒）：{url}") from exc

    if completed.returncode != 0:
        stderr = (completed.stderr or "").strip()[:_STDERR_LIMIT]
        raise ValueError(
            f"git clone 失败（退出码 {completed.returncode}）：{stderr}"
        )

    return dest