"""C-LLM@1/progress@1：进度事件、stderr 渲染与三态开关解析。"""

from __future__ import annotations

import io

from gap_engine.progress import (
    LABEL_ADVICE,
    LABEL_CRITERIA,
    TEXT_MAX_CHARS,
    ProgressEvent,
    resolve_progress,
    stderr_progress,
)


class FakeStream(io.StringIO):
    def __init__(self, tty: bool = False) -> None:
        super().__init__()
        self._tty = tty
        self.flushes = 0

    def isatty(self) -> bool:
        return self._tty

    def flush(self) -> None:
        self.flushes += 1
        super().flush()


def _start(text: str = "高性能", total: int = 3, index: int = 2) -> ProgressEvent:
    return ProgressEvent("start", index, total, LABEL_CRITERIA, text, 0.0)


def _done(text: str = "高性能", total: int = 3, index: int = 2) -> ProgressEvent:
    return ProgressEvent("done", index, total, LABEL_CRITERIA, text, 1.25)


def test_labels_and_text_limit() -> None:
    assert LABEL_CRITERIA == "生成判据"
    assert LABEL_ADVICE == "生成建议"
    assert TEXT_MAX_CHARS == 40


def test_start_writes_no_newline_and_flushes() -> None:
    stream = FakeStream()
    stderr_progress(stream)(_start())

    assert stream.getvalue() == "[2/3] 生成判据：高性能 ..."
    assert stream.flushes == 1


def test_done_carriage_returns_with_seconds_and_newline() -> None:
    stream = FakeStream()
    stderr_progress(stream)(_done())

    assert stream.getvalue() == "\r[2/3] 生成判据：高性能 ... 1.25s\n"
    assert stream.flushes == 1


def test_long_text_truncated_with_ellipsis() -> None:
    stream = FakeStream()
    stream_progress = stderr_progress(stream)
    stream_progress(_start("长" * (TEXT_MAX_CHARS + 5)))

    assert stream.getvalue() == f"[2/3] 生成判据：{'长' * TEXT_MAX_CHARS}… ..."


def test_exact_limit_text_kept_verbatim() -> None:
    stream = FakeStream()
    stderr_progress(stream)(_start("长" * TEXT_MAX_CHARS))

    assert "…" not in stream.getvalue()
    assert "长" * TEXT_MAX_CHARS in stream.getvalue()


def test_resolve_auto_follows_isatty() -> None:
    assert resolve_progress(None, FakeStream(tty=True)) is not None
    assert resolve_progress(None, FakeStream(tty=False)) is None


def test_resolve_explicit_flag_overrides_isatty() -> None:
    assert resolve_progress(True, FakeStream(tty=False)) is not None
    assert resolve_progress(False, FakeStream(tty=True)) is None


def test_renderer_writes_only_given_stream(capsys) -> None:
    stream = FakeStream(tty=True)
    resolve_progress(True, stream)(_done())

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""