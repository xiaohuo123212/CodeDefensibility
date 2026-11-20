#!/usr/bin/env python
"""渲染 · 校验 · 重打包（design.md §2.3 第 7/8 项，覆盖 R1 / R2 / R7）。

一条命令完成：
  1. 校验 src/data/*.json 与 public/ 素材的完整性（含 C-001 音频 sha256、C-002/C-005 源报告 sha256）
  2. npm 依赖就绪 → ``remotion render`` 出 mp4 到 ``out/``
  3. 校验时长 / 分辨率 / H.264+AAC / 音轨存在，再原子移入 ``video/``
  4. 用 ``gap-engine/tools/package.py`` 重打 zip（排除 ``node_modules`` 与 ``out/``）并校验条目

用法：python video/remotion/scripts/render.py [--skip-render] [--skip-package] [--concurrency N]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
from collections.abc import Iterator
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
VIDEO_DIR = ROOT / "video"
REMOTION_DIR = VIDEO_DIR / "remotion"
DATA_DIR = REMOTION_DIR / "src" / "data"
PUBLIC_DIR = REMOTION_DIR / "public"
OUT_DIR = REMOTION_DIR / "out"
ENGINE_DIR = ROOT / "gap-engine"

COMPOSITION_ID = "GapEngineVideo"
FPS = 30
WIDTH = 1920
HEIGHT = 1080
TOTAL_FRAMES = 5040
MAX_DURATION_S = 180.0
EXPECTED_DURATION_S = TOTAL_FRAMES / FPS

# C-V06：以 --scale 超采样渲染，画布逻辑尺寸仍是 1920x1080（组件里的 px 不用改），
# 输出像素按 scale 放大。必须是 1.5 这类能让 1080*scale 落在整数的值——
# 1.333 会得到 1439.64，ffmpeg 拼接直接拒绝。
OUT_SCALE = 1.5
OUT_WIDTH = round(WIDTH * OUT_SCALE)
OUT_HEIGHT = round(HEIGHT * OUT_SCALE)
# CRF 越低画质越好：默认档偏松，14 用于交付母版。
CRF = 14

FINAL_NAME = "对账引擎-eon ego-v1.0-1808931905-演示视频.mp4"
ZIP_NAME = "对账引擎-GapEngine-eon ego-v1.0-1808931905.zip"

DATA_FILES = (
    "narration.json",
    "report-fx-spec.json",
    "report-fx-contradicted.json",
    "terminal.json",
    "daily.json",
)
# design.md §2.3 第 4 项：源 md 变了就必须重跑 prepare_assets.py，否则视频与包内报告互相矛盾
SOURCE_HASH_PAIRS = (
    ("report-fx-spec.json", ENGINE_DIR / "reports" / "fx-spec.md"),
    ("report-fx-contradicted.json", ENGINE_DIR / "reports" / "fx-contradicted.md"),
)

MIN_AUDIO_BYTES = 1024  # C-003 的可用性门槛
MIN_VIDEO_BYTES = 1024 * 1024


class RenderError(RuntimeError):
    """流水线中的可预期失败，提示语直接面向操作者。"""


# ---------------------------------------------------------------- 素材校验


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RenderError(f"{path} 不是合法 JSON：{exc}") from exc


def check_assets() -> dict:
    missing = [name for name in DATA_FILES if not (DATA_DIR / name).is_file()]
    if missing:
        raise RenderError(f"缺少素材 {missing}；先执行 prepare_assets.py")

    narration = read_json(DATA_DIR / "narration.json")
    check_narration(narration)

    terminal = read_json(DATA_DIR / "terminal.json")
    if not terminal.get("ready"):
        detail = "; ".join(item.get("text", "") for item in terminal.get("outputs") or [])
        raise RenderError(f"terminal.json ready=false，S2 命令没有成功执行：{detail}")

    check_source_hashes()
    check_ppt_pages()
    return narration


def check_narration(narration: dict) -> None:
    if not narration.get("fit"):
        raise RenderError("旁白超出镜头槽位（fit=false）：" + "; ".join(narration.get("warnings") or []))
    if narration.get("fps") != FPS or narration.get("totalFrames") != TOTAL_FRAMES:
        raise RenderError(
            f"narration.json 时间轴与 timeline.ts 不一致：fps={narration.get('fps')} "
            f"totalFrames={narration.get('totalFrames')}"
        )

    sentences = narration.get("sentences") or []
    if not sentences or [item.get("id") for item in sentences] != list(range(1, len(sentences) + 1)):
        raise RenderError("narration.json 的 sentences id 不是从 1 连续递增")

    for item in sentences:
        audio = PUBLIC_DIR / str(item.get("audioFile", ""))
        # 人声旁白已由背景音乐替代（Video.tsx 不再引用 audioFile）。
        # 音轨文件若仍存在才校验完整性，避免恢复人声时跳过检查。
        if audio.is_file():
            if audio.stat().st_size < MIN_AUDIO_BYTES:
                raise RenderError(f"旁白音频过小，可能是空文件：{audio.name}")
            if sha256_file(audio) != item.get("audioSha256"):
                raise RenderError(f"旁白音频与 narration.json 记录的 sha256 不一致：{audio.name}")
        start, end = item.get("startFrame"), item.get("endFrame")
        if not isinstance(start, int) or not isinstance(end, int) or not 0 <= start < end <= TOTAL_FRAMES:
            raise RenderError(f"旁白 {item.get('id')} 的帧区间非法：{start}..{end}")

    bgm = PUBLIC_DIR / "audio" / "bgm.wav"
    if not bgm.is_file():
        raise RenderError(f"缺少背景音乐：{bgm}（由 scripts/make_music.py 生成）")
    if bgm.stat().st_size < MIN_AUDIO_BYTES:
        raise RenderError(f"背景音乐过小，可能是空文件：{bgm.name}")

    by_scene: dict[str, list[dict]] = {}
    for item in sentences:
        by_scene.setdefault(str(item.get("scene")), []).append(item)
    for scene_id, group in by_scene.items():
        ordered = sorted(group, key=lambda item: item["startFrame"])
        for prev, nxt in zip(ordered, ordered[1:]):
            if nxt["startFrame"] <= prev["endFrame"]:
                raise RenderError(f"{scene_id} 内旁白 {prev['id']} 与 {nxt['id']} 的帧区间重叠")


def check_source_hashes() -> None:
    for data_name, md_path in SOURCE_HASH_PAIRS:
        if not md_path.is_file():
            raise RenderError(f"缺少源报告：{md_path}")
        payload = read_json(DATA_DIR / data_name)
        if payload.get("sourceSha256") != sha256_file(md_path)[:8]:
            raise RenderError(f"{data_name} 已过期（{md_path.name} 内容已变）；重新执行 prepare_assets.py")


def check_ppt_pages() -> None:
    pages_file = PUBLIC_DIR / "ppt" / "pages.json"
    if not pages_file.is_file():
        raise RenderError(f"缺少 PPT 素材清单：{pages_file}")
    pages = read_json(pages_file).get("pages") or []
    if not pages:
        raise RenderError("pages.json 里没有任何 PPT 页")
    for page in pages:
        path = PUBLIC_DIR / str(page.get("file", ""))
        if not path.is_file():
            raise RenderError(f"缺少 PPT 页图片：{path}")
        if sha256_file(path) != page.get("sha256"):
            raise RenderError(f"PPT 页图片与 pages.json 记录的 sha256 不一致：{path.name}")


# ---------------------------------------------------------------- 渲染


def ensure_dependencies() -> None:
    if (REMOTION_DIR / "node_modules" / "@remotion" / "cli").is_dir():
        return
    npm = shutil.which("npm") or "npm.cmd"
    print("node_modules 缺失，先执行 npm install", flush=True)
    proc = subprocess.run([npm, "install", "--no-audit", "--no-fund"], cwd=REMOTION_DIR)
    if proc.returncode != 0 or not (REMOTION_DIR / "node_modules" / "@remotion" / "cli").is_dir():
        raise RenderError("npm install 失败，无法渲染")


def render_video(concurrency: int | None) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"{COMPOSITION_ID}.mp4"
    out_path.unlink(missing_ok=True)

    npx = shutil.which("npx") or "npx.cmd"
    command = [
        npx,
        "remotion",
        "render",
        COMPOSITION_ID,
        str(out_path),
        "--codec",
        "h264",
        "--audio-codec",
        "aac",
        "--pixel-format",
        "yuv420p",
        "--crf",
        str(CRF),
        "--scale",
        f"{OUT_SCALE}",
    ]
    if concurrency is not None:
        command += ["--concurrency", str(concurrency)]

    print("render: " + " ".join(command), flush=True)
    proc = subprocess.run(command, cwd=REMOTION_DIR)
    if proc.returncode != 0:
        raise RenderError(f"remotion render 失败（exit={proc.returncode}）")
    if not out_path.is_file() or out_path.stat().st_size < MIN_VIDEO_BYTES:
        raise RenderError("渲染没有产出有效 mp4（文件缺失或过小）")
    return out_path


# ---------------------------------------------------------------- mp4 校验
# 不依赖 ffprobe：直接解析 ISO BMFF 盒，校验 R1 要求的分辨率 / 时长 / 编码 / 音轨


def _boxes(data: bytes, start: int, end: int) -> Iterator[tuple[str, int, int]]:
    pos = start
    while pos + 8 <= end:
        size = int.from_bytes(data[pos : pos + 4], "big")
        kind = data[pos + 4 : pos + 8].decode("latin-1")
        header = 8
        if size == 1:
            if pos + 16 > end:
                return
            size = int.from_bytes(data[pos + 8 : pos + 16], "big")
            header = 16
        elif size == 0:
            size = end - pos
        if size < header or pos + size > end:
            return
        yield kind, pos + header, pos + size
        pos += size


def _find_box(data: bytes, start: int, end: int, kind: str) -> tuple[int, int] | None:
    for name, body, stop in _boxes(data, start, end):
        if name == kind:
            return body, stop
    return None


def _find_path(data: bytes, start: int, end: int, path: tuple[str, ...]) -> tuple[int, int] | None:
    span: tuple[int, int] | None = (start, end)
    for kind in path:
        if span is None:
            return None
        span = _find_box(data, span[0], span[1], kind)
    return span


def _track_fields(data: bytes, trak: tuple[int, int]) -> tuple[str, str | None, int, int]:
    handler = ""
    found = _find_path(data, trak[0], trak[1], ("mdia", "hdlr"))
    if found:
        handler = data[found[0] + 8 : found[0] + 12].decode("latin-1")

    codec = None
    stsd = _find_path(data, trak[0], trak[1], ("mdia", "minf", "stbl", "stsd"))
    if stsd:
        entry = stsd[0] + 8  # 跳过 version/flags 与 entry_count
        if entry + 8 <= stsd[1]:
            codec = data[entry + 4 : entry + 8].decode("latin-1")

    width = height = 0
    tkhd = _find_box(data, trak[0], trak[1], "tkhd")
    if tkhd:
        # width/height 是 16.16 定点数，位置随 tkhd 版本不同
        offset = 88 if data[tkhd[0]] == 1 else 76
        width = int.from_bytes(data[tkhd[0] + offset : tkhd[0] + offset + 4], "big") >> 16
        height = int.from_bytes(data[tkhd[0] + offset + 4 : tkhd[0] + offset + 8], "big") >> 16
    return handler, codec, width, height


def probe_mp4(path: Path) -> dict:
    data = path.read_bytes()
    moov = _find_box(data, 0, len(data), "moov")
    if not moov:
        raise RenderError(f"{path.name} 不是可解析的 MP4（缺 moov）")

    mvhd = _find_box(data, moov[0], moov[1], "mvhd")
    if not mvhd:
        raise RenderError(f"{path.name} 缺 mvhd，读不到时长")
    if data[mvhd[0]] == 1:
        timescale = int.from_bytes(data[mvhd[0] + 20 : mvhd[0] + 24], "big")
        duration = int.from_bytes(data[mvhd[0] + 24 : mvhd[0] + 32], "big")
    else:
        timescale = int.from_bytes(data[mvhd[0] + 12 : mvhd[0] + 16], "big")
        duration = int.from_bytes(data[mvhd[0] + 16 : mvhd[0] + 20], "big")
    if not timescale:
        raise RenderError(f"{path.name} 的 mvhd timescale 为 0")

    width = height = 0
    video_codec = audio_codec = None
    for kind, trak_start, trak_end in _boxes(data, moov[0], moov[1]):
        if kind != "trak":
            continue
        handler, codec, track_width, track_height = _track_fields(data, (trak_start, trak_end))
        if handler == "vide":
            video_codec, width, height = codec, track_width, track_height
        elif handler == "soun":
            audio_codec = codec

    return {
        "duration": duration / timescale,
        "width": width,
        "height": height,
        "videoCodec": video_codec,
        "audioCodec": audio_codec,
    }


def check_video(path: Path) -> dict:
    info = probe_mp4(path)
    if info["width"] != OUT_WIDTH or info["height"] != OUT_HEIGHT:
        raise RenderError(
            f"分辨率不符：{info['width']}x{info['height']}，要求 {OUT_WIDTH}x{OUT_HEIGHT}"
        )
    if info["videoCodec"] != "avc1":
        raise RenderError(f"视频编码不是 H.264：{info['videoCodec']}")
    if info["audioCodec"] != "mp4a":
        raise RenderError(f"音轨缺失或编码不是 AAC：{info['audioCodec']}")
    if info["duration"] > MAX_DURATION_S:
        raise RenderError(f"时长超限：{info['duration']:.3f}s > {MAX_DURATION_S:.0f}s")
    if abs(info["duration"] - EXPECTED_DURATION_S) > 2 / FPS:
        raise RenderError(
            f"时长与时间轴不一致：{info['duration']:.3f}s，应为 {EXPECTED_DURATION_S:.3f}s"
        )
    return info


def install_video(source: Path) -> Path:
    VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    target = VIDEO_DIR / FINAL_NAME
    partial = VIDEO_DIR / f"{FINAL_NAME}.part"
    try:
        shutil.move(str(source), str(partial))
        os.replace(partial, target)
    except OSError as exc:
        partial.unlink(missing_ok=True)
        raise RenderError(f"无法把成品视频移入 {VIDEO_DIR}：{exc}") from exc
    return target


# ---------------------------------------------------------------- 重打包


def check_archive(archive: Path) -> int:
    with zipfile.ZipFile(archive) as zf:
        names = zf.namelist()
    if not names:
        raise RenderError("打包结果为空")

    leaked = [
        name
        for name in names
        if name.startswith("video/remotion/node_modules/") or name.startswith("video/remotion/out/")
    ]
    if leaked:
        raise RenderError(f"zip 混入构建产物 {len(leaked)} 项，例如 {leaked[0]}")

    required = [
        f"video/{FINAL_NAME}",
        "video/remotion/package.json",
        "video/remotion/scripts/render.py",
        "video/remotion/src/Video.tsx",
        "video/remotion/src/timeline.ts",
    ]
    missing = [name for name in required if name not in names]
    if missing:
        raise RenderError(f"zip 缺少必要条目：{missing}")
    return len(names)


def repack() -> Path:
    sys.path.insert(0, str(ENGINE_DIR))
    try:
        from tools import package as packager
    finally:
        sys.path.remove(str(ENGINE_DIR))

    dist = ROOT / "dist"
    staging = dist / ".tmp-render"
    shutil.rmtree(staging, ignore_errors=True)

    archive = packager.build(ROOT, staging, name=ZIP_NAME)
    entries = check_archive(archive)
    print(f"archive entries: {entries}")

    dist.mkdir(parents=True, exist_ok=True)
    target = dist / ZIP_NAME
    os.replace(archive, target)
    shutil.rmtree(staging, ignore_errors=True)
    return target


# ---------------------------------------------------------------- 入口


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="渲染演示视频、校验并重新打包交付 zip")
    parser.add_argument("--skip-render", action="store_true", help="复用 out/ 下已渲染的 mp4，只做校验与打包")
    parser.add_argument("--skip-package", action="store_true", help="只渲染并校验，不重新打包")
    parser.add_argument("--concurrency", type=int, default=None, help="remotion 渲染并发数")
    args = parser.parse_args(argv)

    try:
        narration = check_assets()
        print(f"素材校验通过：{len(narration['sentences'])} 句旁白，fit={narration['fit']}", flush=True)

        if not args.skip_render:
            ensure_dependencies()
            render_video(args.concurrency)

        out_path = OUT_DIR / f"{COMPOSITION_ID}.mp4"
        if not out_path.is_file():
            raise RenderError(f"找不到渲染产物 {out_path}；去掉 --skip-render 重跑")
        info = check_video(out_path)
        target = install_video(out_path)
        print(f"video: {target}")
        print(
            f"duration: {info['duration']:.3f}s  {info['width']}x{info['height']}  "
            f"{info['videoCodec']}+{info['audioCodec']}"
        )

        if not args.skip_package:
            print(f"archive: {repack()}")
    except RenderError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())