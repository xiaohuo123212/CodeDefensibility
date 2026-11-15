"""demo 输入源测试（C-DEMO@2）：受控 zip 解压与 GitHub 浅克隆的拒绝/映射行为。"""

from __future__ import annotations

import ast
import io
import subprocess
import zipfile
from pathlib import Path

import pytest

from demo import source

GITHUB_URL = "https://github.com/octo/hello"


def _imported_roots(text: str) -> set[str]:
    roots: set[str] = set()
    for node in ast.walk(ast.parse(text)):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            roots.add(node.module.split(".")[0])
    return roots


def _zip_bytes(entries: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, data in entries.items():
            archive.writestr(name, data)
    return buffer.getvalue()


def _symlink_zip_bytes(name: str, target: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        info = zipfile.ZipInfo(name)
        info.external_attr = 0o120777 << 16
        archive.writestr(info, target)
    return buffer.getvalue()


def _dest(tmp_path: Path) -> Path:
    dest = tmp_path / "dest"
    dest.mkdir()
    return dest


def _completed(command: list[str], returncode: int = 0, stderr: str = ""):
    return subprocess.CompletedProcess(command, returncode, "", stderr)


def _forbid_clone(monkeypatch) -> None:
    def fake_run(*args, **kwargs):
        raise AssertionError("非法 URL 不应触发 git clone")

    monkeypatch.setattr(source.subprocess, "run", fake_run)


def test_constants_match_contract() -> None:
    assert source.MAX_ZIP_BYTES == 20 * 1024 * 1024
    assert source.MAX_UNCOMPRESSED_BYTES == 200 * 1024 * 1024
    assert source.MAX_FILES == 2000
    assert source.CLONE_TIMEOUT == 120


def test_module_uses_stdlib_only_without_shell() -> None:
    text = Path(source.__file__).read_text(encoding="utf-8")

    assert _imported_roots(text) <= {
        "io",
        "os",
        "re",
        "subprocess",
        "zipfile",
        "pathlib",
        "__future__",
    }
    assert "shell=True" not in text


def test_extract_zip_keeps_dest_when_multiple_top_level(tmp_path: Path) -> None:
    blob = _zip_bytes({"pkg/a.py": b"print('a')\n", "README.md": b"hi\n"})
    dest = _dest(tmp_path)

    result = source.extract_zip(blob, dest)

    assert result == dest
    assert (dest / "pkg" / "a.py").read_bytes() == b"print('a')\n"
    assert (dest / "README.md").read_bytes() == b"hi\n"


def test_extract_zip_descends_into_single_top_directory(tmp_path: Path) -> None:
    blob = _zip_bytes(
        {"repo-abc/README.md": b"hi\n", "repo-abc/src/main.py": b"x = 1\n"}
    )
    dest = _dest(tmp_path)

    result = source.extract_zip(blob, dest)

    assert result == dest / "repo-abc"
    assert (result / "src" / "main.py").read_bytes() == b"x = 1\n"


def test_extract_zip_does_not_delete_dest(tmp_path: Path) -> None:
    dest = _dest(tmp_path)

    source.extract_zip(_zip_bytes({"a.txt": b"a"}), dest)

    assert dest.is_dir()


def test_extract_zip_rejects_invalid_blob(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        source.extract_zip(b"definitely not a zip", _dest(tmp_path))


@pytest.mark.parametrize(
    "name",
    [
        "../evil.txt",
        "pkg/../../evil.txt",
        "/etc/passwd",
        "\\abs.txt",
        "C:/evil.txt",
        "C:evil.txt",
    ],
)
def test_extract_zip_rejects_unsafe_member_names(
    tmp_path: Path, name: str
) -> None:
    dest = _dest(tmp_path)

    with pytest.raises(ValueError):
        source.extract_zip(_zip_bytes({name: b"pwn"}), dest)

    assert not (tmp_path / "evil.txt").exists()
    assert list(dest.iterdir()) == []


def test_extract_zip_rejects_symlink_member(tmp_path: Path) -> None:
    blob = _symlink_zip_bytes("link", "../../etc/passwd")

    with pytest.raises(ValueError, match="符号链接"):
        source.extract_zip(blob, _dest(tmp_path))


def test_extract_zip_rejects_blob_over_size_limit(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(source, "MAX_ZIP_BYTES", 128)
    blob = _zip_bytes({"a.txt": b"x" * 4096})

    with pytest.raises(ValueError, match="128"):
        source.extract_zip(blob, _dest(tmp_path))


def test_extract_zip_rejects_too_many_files(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(source, "MAX_FILES", 2)
    blob = _zip_bytes({f"f{index}.txt": b"x" for index in range(3)})

    with pytest.raises(ValueError, match="3 超过上限 2"):
        source.extract_zip(blob, _dest(tmp_path))


def test_extract_zip_rejects_too_many_uncompressed_bytes(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(source, "MAX_UNCOMPRESSED_BYTES", 16)
    blob = _zip_bytes({"big.txt": b"x" * 64})

    with pytest.raises(ValueError, match="16"):
        source.extract_zip(blob, _dest(tmp_path))


def test_clone_github_runs_shallow_clone_without_shell(
    tmp_path: Path, monkeypatch
) -> None:
    dest = _dest(tmp_path)
    calls: list[tuple[list[str], dict]] = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        (dest / "README.md").write_text("hi\n", encoding="utf-8")
        return _completed(command)

    monkeypatch.setattr(source.subprocess, "run", fake_run)

    assert source.clone_github(GITHUB_URL, dest) == dest
    assert len(calls) == 1
    command, options = calls[0]
    assert command == ["git", "clone", "--depth", "1", "--quiet", GITHUB_URL, str(dest)]
    assert not options.get("shell")
    assert options["timeout"] == source.CLONE_TIMEOUT
    assert options["capture_output"] is True
    assert options["text"] is True
    assert options["env"]["GIT_TERMINAL_PROMPT"] == "0"


def test_clone_github_accepts_dot_git_suffix(tmp_path: Path, monkeypatch) -> None:
    dest = _dest(tmp_path)
    monkeypatch.setattr(
        source.subprocess, "run", lambda command, **kwargs: _completed(command)
    )

    assert source.clone_github("https://github.com/octo/hello.git", dest) == dest


@pytest.mark.parametrize(
    "url",
    [
        "",
        "http://github.com/octo/hello",
        "git@github.com:octo/hello.git",
        "https://gitlab.com/octo/hello",
        "https://github.com/octo",
        "https://github.com/octo/hello/extra",
        "https://user@github.com/octo/hello",
        "https://github.com:443/octo/hello",
        "https://github.com/octo/hello?tab=readme",
    ],
)
def test_clone_github_rejects_invalid_urls(
    tmp_path: Path, monkeypatch, url: str
) -> None:
    _forbid_clone(monkeypatch)

    with pytest.raises(ValueError):
        source.clone_github(url, tmp_path / "repo")


def test_clone_github_maps_timeout_to_timeout_error(
    tmp_path: Path, monkeypatch
) -> None:
    def fake_run(command, **kwargs):
        raise subprocess.TimeoutExpired(command, kwargs["timeout"])

    monkeypatch.setattr(source.subprocess, "run", fake_run)

    with pytest.raises(TimeoutError) as excinfo:
        source.clone_github(GITHUB_URL, tmp_path / "repo")

    assert isinstance(excinfo.value, OSError)
    assert str(source.CLONE_TIMEOUT) in str(excinfo.value)


def test_clone_github_maps_failure_to_valueerror_with_truncated_stderr(
    tmp_path: Path, monkeypatch
) -> None:
    stderr = "fatal: repository not found " + "x" * 300 + "TAIL_MARKER"
    monkeypatch.setattr(
        source.subprocess,
        "run",
        lambda command, **kwargs: _completed(command, 128, stderr),
    )

    with pytest.raises(ValueError) as excinfo:
        source.clone_github(GITHUB_URL, tmp_path / "repo")

    message = str(excinfo.value)
    assert "128" in message
    assert stderr[:200] in message
    assert "TAIL_MARKER" not in message