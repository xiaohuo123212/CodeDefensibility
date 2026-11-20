#!/usr/bin/env python
"""一条命令产出 Remotion 视频的全部真实素材（design.md §2.2 C-001 ~ C-006）。

产出：
  video/remotion/src/data/narration.json               24 句旁白 + 帧区间（C-001）
  video/remotion/src/data/report-fx-spec.json          fx-spec.md 结构化（C-002）
  video/remotion/src/data/report-fx-contradicted.json  fx-contradicted.md 结构化（C-005）
  video/remotion/src/data/terminal.json                S2 命令真实执行结果（C-006）
  video/remotion/src/data/daily.json                   留痕目录真实枚举（C-009）
  video/remotion/public/audio/01.mp3 … 24.mp3          edge-tts 合成（C-003）
  video/remotion/public/ppt/P13.png, P15.png, pages.json  PDF 渲染（C-004）

用法：python video/remotion/scripts/prepare_assets.py [--force-tts]
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import edge_tts
import pymupdf

ROOT = Path(__file__).resolve().parents[3]
ENGINE_DIR = ROOT / "gap-engine"
SPEECH_MD = ROOT / "video" / "视频稿.md"
PPT_PDF = ROOT / "ppt" / "对账引擎-初赛-放映版.pdf"
FX_SPEC_MD = ENGINE_DIR / "reports" / "fx-spec.md"
FX_CONTRA_MD = ENGINE_DIR / "reports" / "fx-contradicted.md"

OUT_DIR = ROOT / "video" / "remotion"
DATA_DIR = OUT_DIR / "src" / "data"
AUDIO_DIR = OUT_DIR / "public" / "audio"
PPT_OUT_DIR = OUT_DIR / "public" / "ppt"

FPS = 30
TOTAL_FRAMES = 5040
VOICE = "zh-CN-XiaoxiaoNeural"
TTS_RATE = "-5%"
LEAD_IN_FRAMES = 6
GAP_FRAMES = 6

# design.md §2.1 时间轴（绝对帧），与 T2 的 src/timeline.ts 保持一致
SCENES: dict[str, tuple[int, int]] = {
    "S1": (0, 456),
    "S2": (456, 864),
    "S3": (864, 1284),
    "S4": (1284, 3324),
    "S5": (3324, 3864),
    "S6": (3864, 4524),
    "S7": (4524, 5040),
}

# 视频稿 S2 画面里敲的那条命令，必须在终端里真跑一遍（C-006）
DEMO_CWD = Path(r"C:\demo\gap-engine")
DEMO_PROMPT = "demo>"
DAILY_DIR_LABEL = "codearts_proof/daily/"
DAILY_DEMO_DIR = Path(r"C:\demo\codearts_proof\daily")
DAILY_SRC_DIR = ROOT / "codearts_proof" / "daily"
TERMINAL_COMMAND = (
    "gap spec contract\\fixtures\\fx-spec "
    "--spec contract\\fixtures\\fx-spec\\requirements.md "
    "--out reports\\fx-spec.md"
)
TERMINAL_REPORT_PATH = "reports\\fx-spec.md"
PPT_PAGES = (13, 15)

CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳㉑㉒㉓㉔"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    path.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------- 旁白文本与镜头


def parse_narration_texts(md: str) -> list[tuple[int, str]]:
    """从「三、旁白连读版」取 24 句正文（不含编号），顺序即 id。"""
    match = re.search(r"^## 三、.*?$(.*?)^---", md, re.M | re.S)
    if not match:
        raise RuntimeError("视频稿中找不到「三、旁白连读版」段落")
    sentences = re.findall(r"^(\d+)\.\s+(.+?)\s*$", match.group(1), re.M)
    items = [(int(no), text) for no, text in sentences]
    items.sort(key=lambda pair: pair[0])
    if [no for no, _ in items] != list(range(1, 25)):
        raise RuntimeError(f"旁白编号不是 1..24：{[no for no, _ in items]}")
    return items


def parse_screen_copy(md: str) -> tuple[list[str], str]:
    """从「四、字幕清单」取 S1 标题两行与 S7 收尾一行（屏幕文案，非旁白文本）。"""
    section = re.search(r"^## 四、字幕清单(.*?)^---", md, re.M | re.S)
    if not section:
        raise RuntimeError("视频稿中找不到「四、字幕清单」段落")
    rows: dict[str, str] = {}
    for line in section.group(1).splitlines():
        match = re.match(r"^\|\s*(S[17])\s*[^|]*\|(.+)\|\s*$", line)
        if match:
            rows[match.group(1)] = match.group(2)
    if "S1" not in rows or "S7" not in rows:
        raise RuntimeError(f"字幕清单缺少 S1/S7 行：{sorted(rows)}")
    s1_titles = [cell.strip().strip("`").strip() for cell in rows["S1"].split("` / `")]
    s7_outro = rows["S7"].strip().strip("`").strip()
    return s1_titles, s7_outro


def parse_scene_map(md: str) -> dict[int, str]:
    """从「二、逐镜头稿」的 ① … ㉔ 编号推出每句所属镜头（S4a→S4）。"""
    match = re.search(r"^## 二、.*?^## 三、", md, re.M | re.S)
    if not match:
        raise RuntimeError("视频稿中找不到「二、逐镜头稿」段落")
    section = match.group(0)
    scene_of: dict[int, str] = {}
    current = ""
    for line in section.splitlines():
        heading = re.match(r"^###\s+(S\d)", line)
        if heading:
            current = heading.group(1)
            continue
        bullet = re.match(r"^\s+-\s+([\u2460-\u2473\u3251-\u3254])\s+", line)
        if bullet and current:
            index = CIRCLED.index(bullet.group(1)) + 1
            scene_of.setdefault(index, current)
    missing = sorted(set(range(1, 25)) - set(scene_of))
    if missing:
        raise RuntimeError(f"逐镜头稿里缺少这些编号的旁白：{missing}")
    return scene_of


# ---------------------------------------------------------------- TTS（C-001/C-003）


def load_previous(path: Path) -> tuple[dict[int, dict], str | None, str | None]:
    """返回上一轮的 (句子表, 顶层 voice, 顶层 rate)；voice/rate 用于判定音色是否换过。"""
    if not path.exists():
        return {}, None, None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}, None, None
    sentences = {item["id"]: item for item in payload.get("sentences", []) if "id" in item}
    return sentences, payload.get("voice"), payload.get("rate")


async def synthesize(text: str, out_path: Path) -> int:
    communicate = edge_tts.Communicate(text, VOICE, rate=TTS_RATE)
    audio = bytearray()
    duration_ticks = 0
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio.extend(chunk["data"])
        elif chunk["type"] in ("WordBoundary", "SentenceBoundary"):
            duration_ticks = max(duration_ticks, chunk["offset"] + chunk["duration"])
    if not audio or duration_ticks <= 0:
        raise RuntimeError(f"TTS 未返回音频或时间戳：{out_path.name}")
    out_path.write_bytes(bytes(audio))
    return int(round(duration_ticks / 10_000))


async def build_audio(
    sentences: list[dict], previous: dict[int, dict], force: bool, voice_matches: bool
) -> list[int]:
    """voice_matches 为 False 时缓存不可信（音色/语速已换），必须全部重合成。"""
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    regenerated: list[int] = []
    for item in sentences:
        audio_path = AUDIO_DIR / f"{item['id']:02d}.mp3"
        old = previous.get(item["id"])
        reusable = (
            not force
            and voice_matches
            and old is not None
            and audio_path.exists()
            and audio_path.stat().st_size > 1024
            and old.get("audioSha256") == sha256_file(audio_path)
            and isinstance(old.get("durationMs"), int)
        )
        if reusable:
            item["durationMs"] = old["durationMs"]
            item["audioSha256"] = old["audioSha256"]
            continue
        item["durationMs"] = await synthesize(item["text"], audio_path)
        item["audioSha256"] = sha256_file(audio_path)
        regenerated.append(item["id"])
    return regenerated


# ---------------------------------------------------------------- 帧排布


def layout_frames(sentences: list[dict], warnings: list[str]) -> bool:
    fit = True
    for scene_id, (scene_start, scene_end) in SCENES.items():
        cursor = scene_start + LEAD_IN_FRAMES
        for item in sentences:
            if item["scene"] != scene_id:
                continue
            start = cursor
            end = start + int(round(item["durationMs"] * FPS / 1000))
            item["startFrame"] = start
            item["endFrame"] = end
            cursor = end + GAP_FRAMES
        if cursor - GAP_FRAMES > scene_end:
            fit = False
            overflow = cursor - GAP_FRAMES - scene_end
            warnings.append(f"{scene_id} overflow: +{overflow} frames")
    missing = [item["id"] for item in sentences if "startFrame" not in item]
    if missing:
        raise RuntimeError(f"这些句子没有被排进任何镜头：{missing}")
    return fit


def build_narration(force_tts: bool, extra_warnings: list[str]) -> None:
    md = SPEECH_MD.read_text(encoding="utf-8")
    texts = parse_narration_texts(md)
    scene_of = parse_scene_map(md)
    s1_titles, s7_outro = parse_screen_copy(md)
    previous, prev_voice, prev_rate = load_previous(DATA_DIR / "narration.json")
    voice_matches = prev_voice == VOICE and prev_rate == TTS_RATE

    sentences: list[dict] = [
        {
            "id": index,
            "no": CIRCLED[index - 1],
            "scene": scene_of[index],
            "text": text,
            "audioFile": f"audio/{index:02d}.mp3",
        }
        for index, text in texts
    ]
    regenerated = asyncio.run(
        build_audio(sentences, previous, force=force_tts, voice_matches=voice_matches)
    )

    warnings = list(extra_warnings)
    fit = layout_frames(sentences, warnings)

    scenes = [
        {
            "id": scene_id,
            "startFrame": start,
            "endFrame": end,
            "sentenceIds": [item["id"] for item in sentences if item["scene"] == scene_id],
        }
        for scene_id, (start, end) in SCENES.items()
    ]
    write_json(
        DATA_DIR / "narration.json",
        {
            "fps": FPS,
            "totalFrames": TOTAL_FRAMES,
            "voice": VOICE,
            "rate": TTS_RATE,
            "fit": fit,
            "warnings": warnings,
            "s1Titles": s1_titles,
            "s7Outro": s7_outro,
            "sentences": sentences,
            "scenes": scenes,
        },
    )
    print(f"narration.json  {len(sentences)} 句  fit={fit}  warnings={warnings}")
    print(f"  voice={VOICE} rate={TTS_RATE} 重合成 {len(regenerated)} 句")


# ---------------------------------------------------------------- fx-spec（C-002）


def split_sections(md: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current = ""
    for line in md.splitlines():
        heading = re.match(r"^##\s+(.+?)\s*$", line)
        if heading:
            current = heading.group(1)
            sections[current] = []
            continue
        if current:
            sections[current].append(line)
    return sections


def strip_bullet(line: str) -> str:
    return re.sub(r"^\s*-\s+", "", line).strip()


def parse_missing(lines: list[str]) -> list[dict]:
    items = []
    for line in lines:
        match = re.match(r"^-\s+(.+?)：(\d+) 处（扫过 (\d+) 处）$", line.strip())
        if match:
            items.append(
                {"type": match.group(1), "count": int(match.group(2)), "scanned": int(match.group(3))}
            )
    return items


def parse_found(lines: list[str]) -> list[dict]:
    items: list[dict] = []
    for line in lines:
        head = re.match(r"^-\s+(.+?)：(\d+) 处$", line)
        if head:
            items.append({"type": head.group(1), "count": int(head.group(2)), "locations": []})
            continue
        location = re.match(r"^\s+-\s+(\S.*)$", line)
        if location and items:
            items[-1]["locations"].append(location.group(1).strip())
    return items


def parse_item_block(block: list[str]) -> dict:
    item = {
        "title": "",
        "sourceLine": "",
        "found": [],
        "missing": [],
        "conclusion": "",
        "question": "",
        "todo": "",
    }
    bucket = ""
    found_lines: list[str] = []
    missing_lines: list[str] = []
    for raw in block:
        line = raw.strip()
        if not line:
            continue
        if line == "查到：":
            bucket = "found"
            continue
        if line == "查过没找到：":
            bucket = "missing"
            continue
        if bucket == "found":
            found_lines.append(raw)
            continue
        if bucket == "missing":
            if re.match(r"^-\s+", line):
                missing_lines.append(raw)
                continue
            bucket = ""
        for prefix, key in (
            ("来源：", "sourceLine"),
            ("结论：", "conclusion"),
            ("换假设：", "hypothesis"),
            ("会被问：", "question"),
            ("该补什么：", "todo"),
            ("audit effort：", "auditEffort"),
        ):
            if line.startswith(prefix):
                # C-002 示例里只有 hypothesis 保留「换假设：」前缀，其余字段只留值
                item[key] = line if key == "hypothesis" else line[len(prefix) :].strip()
                break
        else:
            if line.startswith("- 判据：") or line.startswith("判据："):
                item["criteria"] = re.sub(r"^-?\s*判据：", "", line).strip()

    item["found"] = parse_found(found_lines)
    item["missing"] = parse_missing(missing_lines)
    return item


def build_report_spec() -> None:
    md = FX_SPEC_MD.read_text(encoding="utf-8")
    sections = split_sections(md)
    lines = md.splitlines()
    title = re.sub(r"^#\s+", "", lines[0]).strip()
    lead = next(line.strip() for line in lines[1:] if line.strip())

    precheck_lines = [line for line in sections.get("需求可判定性预检", []) if line.strip()]
    precheck_summary = next(line.strip() for line in precheck_lines if line.startswith("共 "))
    precheck_items = []
    for line in precheck_lines:
        match = re.match(r'^-\s+`(.*?)`\s+"(.*?)"\s+→\s+(.+)$', line.strip())
        if match:
            precheck_items.append(
                {
                    "location": match.group(1),
                    "term": match.group(2),
                    "criteria": match.group(3).strip(),
                }
            )

    overview_lines = [line.strip() for line in sections.get("概览", []) if line.strip()]
    scanned = next(line.lstrip("#").strip() for line in overview_lines if line.startswith("#"))
    distinct = next(strip_bullet(line) for line in overview_lines if "其中不同位置" in line)
    verdict = next(strip_bullet(line) for line in overview_lines if "有证据" in line)

    items = []
    for block in re.split(r"^###\s+", "\n".join(sections.get("逐条", [])), flags=re.M)[1:]:
        block_lines = block.splitlines()
        parsed = parse_item_block(block_lines[1:])
        parsed["title"] = block_lines[0].strip()
        items.append(parsed)

    limits = [
        strip_bullet(line) for line in sections.get("局限", []) if line.strip().startswith("-")
    ]
    write_json(
        DATA_DIR / "report-fx-spec.json",
        {
            "title": title,
            "lead": lead,
            "sourceMd": "gap-engine/reports/fx-spec.md",
            "sourceSha256": sha256_file(FX_SPEC_MD)[:8],
            "precheck": {
                "heading": "需求可判定性预检",
                "summary": precheck_summary,
                "items": precheck_items,
            },
            "overview": {
                "heading": "概览",
                "scanned": scanned,
                "distinct": distinct,
                "verdict": verdict,
            },
            "items": items,
            "limits": {"heading": "局限", "lines": limits},
        },
    )
    print(f"report-fx-spec.json  items={len(items)}  missing={sum(len(i['missing']) for i in items)}")


# ---------------------------------------------------------------- fx-contradicted（C-005）


def build_report_contradicted() -> None:
    md = FX_CONTRA_MD.read_text(encoding="utf-8")
    lines = md.splitlines()
    title = re.sub(r"^#\s+", "", lines[0]).strip()

    first_item = md.split("### ", 1)[1]
    item_lines = [strip_bullet(line) for line in first_item.splitlines() if line.strip()]
    conclusion = next(line for line in item_lines if line.startswith("结论："))
    location = next(line for line in item_lines if line.startswith("定位："))
    question = next(line for line in item_lines if line.startswith("会被问："))

    evidence: list[str] = []
    collecting = False
    for line in item_lines:
        if line == "查到：":
            collecting = True
            continue
        if collecting and line == "查过没找到：":
            break
        if collecting:
            evidence.append(line)

    write_json(
        DATA_DIR / "report-fx-contradicted.json",
        {
            "title": title,
            "sourceMd": "gap-engine/reports/fx-contradicted.md",
            "sourceSha256": sha256_file(FX_CONTRA_MD)[:8],
            "conclusionLine": conclusion,
            "locationLine": location,
            "requirementLine": question,
            "evidenceLines": evidence,
        },
    )
    print(f"report-fx-contradicted.json  location={location}  evidence={len(evidence)}")


# ---------------------------------------------------------------- PPT（C-004）


def build_ppt_pages() -> None:
    PPT_OUT_DIR.mkdir(parents=True, exist_ok=True)
    document = pymupdf.open(PPT_PDF)
    pages = []
    for page_no in PPT_PAGES:
        page = document[page_no - 1]
        zoom = 1920 / page.rect.width
        pixmap = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
        out_path = PPT_OUT_DIR / f"P{page_no}.png"
        pixmap.save(out_path)
        pages.append(
            {
                "file": f"ppt/P{page_no}.png",
                "page": page_no,
                "width": pixmap.width,
                "height": pixmap.height,
                "sha256": sha256_file(out_path),
            }
        )
    document.close()
    write_json(PPT_OUT_DIR / "pages.json", {"pages": pages})
    print(f"pages.json  {[page['file'] for page in pages]}")


# ---------------------------------------------------------------- 终端（C-006）


def build_terminal() -> None:
    fixture_src = ENGINE_DIR / "contract" / "fixtures" / "fx-spec"
    fixture_dst = DEMO_CWD / "contract" / "fixtures" / "fx-spec"
    shutil.copytree(fixture_src, fixture_dst, dirs_exist_ok=True)
    (DEMO_CWD / "reports").mkdir(parents=True, exist_ok=True)
    report_file = DEMO_CWD / "reports" / "fx-spec.md"
    report_file.unlink(missing_ok=True)

    proc = subprocess.run(
        TERMINAL_COMMAND,
        shell=True,
        cwd=DEMO_CWD,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    outputs = [
        {"text": line, "kind": kind}
        for kind, stream in (("out", proc.stdout), ("err", proc.stderr))
        for line in stream.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        if line.strip()
    ]
    write_json(
        DATA_DIR / "terminal.json",
        {
            "ready": proc.returncode == 0 and report_file.exists(),
            "cwd": str(DEMO_CWD),
            "prompt": DEMO_PROMPT,
            "commandLine": TERMINAL_COMMAND,
            "outputs": outputs,
            "exitCode": proc.returncode,
            "reportPath": TERMINAL_REPORT_PATH,
            "capturedAt": datetime.now().isoformat(timespec="seconds"),
        },
    )
    print(f"terminal.json  exit={proc.returncode}  outputs={[o['text'] for o in outputs]}")


def build_daily() -> str | None:
    """枚举 C:\\demo\\codearts_proof\\daily\\*.md（C-009），返回需要记入 warnings 的原因。"""
    if not DAILY_DEMO_DIR.exists():
        if not DAILY_SRC_DIR.exists():
            write_json(DATA_DIR / "daily.json", _daily_payload([]))
            return f"{DAILY_DIR_LABEL} 目录不存在"
        shutil.copytree(DAILY_SRC_DIR, DAILY_DEMO_DIR, dirs_exist_ok=True)
    files = sorted(
        (path.name for path in DAILY_DEMO_DIR.glob("*.md")),
        key=lambda name: (int(m.group(1)) if (m := re.match(r"^D(\d+)", name)) else 10**6, name),
    )
    write_json(DATA_DIR / "daily.json", _daily_payload(files))
    print(f"daily.json  files={files}")
    return None if files else f"{DAILY_DIR_LABEL} 下没有 .md 文件"


def _daily_payload(files: list[str]) -> dict:
    return {
        "dirLabel": DAILY_DIR_LABEL,
        "sourceDir": str(DAILY_DEMO_DIR),
        "files": files,
    }


def main(force_tts: bool) -> int:
    for path in (SPEECH_MD, FX_SPEC_MD, FX_CONTRA_MD, PPT_PDF):
        if not path.exists():
            print(f"缺少输入文件：{path}", file=sys.stderr)
            return 1
    daily_warning = build_daily()
    build_narration(force_tts, [daily_warning] if daily_warning else [])
    build_report_spec()
    build_report_contradicted()
    build_ppt_pages()
    build_terminal()
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="生成 Remotion 视频所需素材")
    parser.add_argument("--force-tts", action="store_true", help="忽略缓存，重新合成全部旁白音频")
    args = parser.parse_args()
    sys.exit(main(force_tts=args.force_tts))