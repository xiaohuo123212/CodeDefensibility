"""调用进度反馈：AI 子命令的 stderr 进度事件（C-LLM@1/progress@1）。

进度只写调用方传入的 stream：不写 stdout、不写任何文件，因此产物字节与
「报告逐字可比」的前提不受影响；管道/重定向/CI 下默认静默。
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TextIO

LABEL_CRITERIA = "生成判据"
LABEL_ADVICE = "生成建议"
TEXT_MAX_CHARS = 40

PHASE_START = "start"
PHASE_DONE = "done"

__all__ = [
    "LABEL_ADVICE",
    "LABEL_CRITERIA",
    "PHASE_DONE",
    "PHASE_START",
    "TEXT_MAX_CHARS",
    "ProgressEvent",
    "ProgressFn",
    "resolve_progress",
    "stderr_progress",
]


@dataclass(frozen=True)
class ProgressEvent:
    phase: str
    index: int
    total: int
    label: str
    text: str
    seconds: float


ProgressFn = Callable[[ProgressEvent], None]


def stderr_progress(stream: TextIO) -> ProgressFn:
    def emit(event: ProgressEvent) -> None:
        head = f"[{event.index}/{event.total}] {event.label}：{_shorten(event.text)}"
        if event.phase == PHASE_START:
            stream.write(f"{head} ...")
        else:
            stream.write(f"\r{head} ... {event.seconds:.2f}s\n")
        stream.flush()

    return emit


def resolve_progress(flag: bool | None, stream: TextIO) -> ProgressFn | None:
    if flag is None:
        return stderr_progress(stream) if stream.isatty() else None
    return stderr_progress(stream) if flag else None


def _shorten(text: str) -> str:
    if len(text) <= TEXT_MAX_CHARS:
        return text
    return text[:TEXT_MAX_CHARS] + "…"