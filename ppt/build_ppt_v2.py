"""从 final.pptx 母版生成比赛定稿 pptx。

每次运行都从 SRC 重新复制覆盖 DST，再做四处定点修正：
全局去色、章节序号、右下角页码、指标页标签，因此重复执行结果一致。
"""

from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

SRC: str = r"C:\Users\haoll\Downloads\final.pptx"
DST: str = "ppt/对账引擎-初赛.pptx"

SLIDE_COUNT = 18
CHAPTER_SLIDE_INDEX = 13  # 第 14 页：第四章章节页，序号 004 → 04
CARD_SLIDE_INDEXES = (8, 16)  # 第 9、17 页：四栏卡
METRICS_SLIDE_INDEX = 12  # 第 13 页：指标页

CHAPTER_OLD, CHAPTER_NEW = "004", "04"

PAGE_NUMBER_BOX = (Inches(11.40), Inches(7.02), Inches(1.36), Inches(0.24))
PAGE_NUMBER_COLOR = "8C8C8C"

# 背景与文字只留黑白灰：大面积色块按原明度压成同一套深灰阶，
# 强调色只保留 ACCENT，且只落在序号、指标数字与每页小标签上。
ACCENT = "21B8C7"
NEUTRAL_FILL_MAP = {
    "6AD7E5": "3A3A3A",
    "21B8C7": "333333",
    "0A7F8B": "2C2C2C",
    "12293E": "222222",
    "0E1F2F": "181818",
}
CARD_FILLS = ("6AD7E5", "0A7F8B", "12293E")

NEUTRAL_TEXT_LIGHT = "F2F2F2"  # 大标题
NEUTRAL_TEXT_BODY = "D9D9D9"  # 正文
NEUTRAL_TEXT_DARK = "1A1A1A"  # 浅色底上的字
TITLE_MIN_FONT_PT = 29.0
INDEX_MIN_FONT_PT = 16.0

# 每页一枚小标签，是全篇唯一允许保留的强调文字之一
ACCENT_EYEBROWS = frozenset(
    {
        "THE GAP", "CONTRACT SPLIT", "PIPELINE", "VERDICT", "HIGHLIGHTS",
        "ENGINEERING", "METRICS", "LIMITS", "LESSONS", "ROADMAP",
    }
)

METRIC_LABELS = {"N=?": "认可率", "25": "样本条目", "5": "项目数"}
METRIC_NUM_PT = 40.0
METRIC_ACCENT = ACCENT
METRIC_LABEL_PT = 8.88
METRIC_LABEL_COLOR = "D9D9D9"
METRIC_LABEL_WIDTH = Inches(1.2)
METRIC_LABEL_HEIGHT = Inches(0.16)

# 指标页左侧数字块（右边界 4.29in）与右侧说明列（左边界 7.17in）之间是唯一空白竖带。
# 该竖带被三条全宽细线（T4.19 / T5.38 / T6.56）切成三条横带，所以拆成三个文本框分别落带，
# 每个框底边都留在线之上，避免分隔线从文字中间穿过。
MEASURED_LEFT = Inches(4.40)
MEASURED_WIDTH = Inches(2.62)
MEASURED_TITLE_PT = 12.0
MEASURED_BODY_PT = 11.0
MEASURED_FONT = "MiSans VF Light"

# 每框：(top, height, ((字号, 底色, ((文本, 是否强调色), ...)), ...))
# 每段是一组 (文本, 是否强调色)；数字用 ACCENT，其余用正文灰
MEASURED_BOXES = (
    (Inches(3.29), Inches(0.86), (
        (MEASURED_TITLE_PT, NEUTRAL_TEXT_LIGHT, (("乙组·人工真值（不依赖回执）", False),)),
        (MEASURED_BODY_PT, NEUTRAL_TEXT_BODY, (
            ("真实现 N=32：precision ", False), ("8/8 = 100%", True),
            ("　recall ", False), ("8/32 = 25%", True),
        )),
        (MEASURED_BODY_PT, NEUTRAL_TEXT_BODY, (
            ("（可判 27 条 ", False), ("8/27 = 29.6%", True), ("）", False),
        )),
    )),
    (Inches(4.23), Inches(1.12), (
        (MEASURED_BODY_PT, NEUTRAL_TEXT_BODY, (
            ("真反证 N=30：召回 ", False), ("1/30 = 3.3%", True),
            ("　唯一定位 ", False), ("1/1 = 100%", True),
        )),
        (MEASURED_BODY_PT, NEUTRAL_TEXT_BODY, (
            ("反向错误 ", False), ("6/30 = 20%", True),
            ("　漏报 ", False), ("23/30 = 76.7%", True),
        )),
        (MEASURED_BODY_PT, NEUTRAL_TEXT_BODY, (("偏置：真值取自自述，反证仅「明写」", False),)),
    )),
    (Inches(5.42), Inches(1.10), (
        (MEASURED_BODY_PT, NEUTRAL_TEXT_BODY, (
            ("版本对照：@8 反向 ", False), ("2/10 = 20%", True),
        )),
        (MEASURED_BODY_PT, NEUTRAL_TEXT_BODY, (
            ("@9 修复前反向 ", False), ("18/30 = 60%", True),
            ("；@10 修复后反向 ", False), ("6/30 = 20%", True),
        )),
        (MEASURED_BODY_PT, NEUTRAL_TEXT_BODY, (
            ("召回 ", False), ("1/10 = 10%", True), ("、", False), ("1/30 = 3.3%", True),
            ("；判据敏感，引用须带版本号", False),
        )),
    )),
)

# 无字体文件可测量时按字符 em 宽度近似，只用于把标签订在数字右侧
_CHAR_WIDTH_EM = {
    "N": 0.72, "=": 0.62, "?": 0.55,
    "0": 0.6, "1": 0.6, "2": 0.6, "3": 0.6, "4": 0.6,
    "5": 0.6, "6": 0.6, "7": 0.6, "8": 0.6, "9": 0.6,
}


def _dst_path() -> Path:
    """DST 按仓库根解析，避免受调用时工作目录影响。"""
    return Path(__file__).resolve().parent.parent / DST


def _iter_runs(shape):
    for paragraph in shape.text_frame.paragraphs:
        for run in paragraph.runs:
            yield run


def _solid_fill_rgb(shape):
    try:
        if shape.fill.type != 1:  # MSO_FILL.SOLID
            return None
        rgb = shape.fill.fore_color.rgb
    except (AttributeError, TypeError, ValueError):
        return None
    return str(rgb).upper()


def _shape_max_font_pt(shape) -> float:
    sizes = [run.font.size.pt for run in _iter_runs(shape) if run.font.size]
    return max(sizes) if sizes else 0.0



def fix_chapter_number(prs) -> None:
    slide = prs.slides[CHAPTER_SLIDE_INDEX]
    for shape in slide.shapes:
        if shape.has_text_frame and shape.text_frame.text.strip() == CHAPTER_OLD:
            for run in _iter_runs(shape):
                if CHAPTER_OLD in run.text:
                    run.text = run.text.replace(CHAPTER_OLD, CHAPTER_NEW)
                    return
    raise RuntimeError(f"第 {CHAPTER_SLIDE_INDEX + 1} 页未找到章节序号 {CHAPTER_OLD}")


def add_page_numbers(prs) -> None:
    total = len(prs.slides)
    left, top, width, height = PAGE_NUMBER_BOX
    for index, slide in enumerate(prs.slides, start=1):
        box = slide.shapes.add_textbox(left, top, width, height)
        frame = box.text_frame
        frame.word_wrap = False
        frame.margin_left = 0
        frame.margin_right = 0
        frame.margin_top = 0
        frame.margin_bottom = 0
        paragraph = frame.paragraphs[0]
        paragraph.alignment = PP_ALIGN.RIGHT
        run = paragraph.add_run()
        run.text = f"{index:02d} / {total:02d}"
        run.font.size = Pt(9)
        run.font.name = "Didot"
        run.font.color.rgb = RGBColor.from_string(PAGE_NUMBER_COLOR)


def _iter_shapes(shapes):
    for shape in shapes:
        yield shape
        if getattr(shape, "shapes", None) is not None:
            yield from _iter_shapes(shape.shapes)


def _relative_luminance(hex_rgb: str) -> float:
    channels = [int(hex_rgb[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _backdrop_rgb(shapes, target):
    """取中心点落在其内、面积最小的纯色形状的填充色，作为文字所在底色。"""
    cx = target.left + target.width // 2
    cy = target.top + target.height // 2
    best = None
    for shape in shapes:
        if shape is target:
            continue
        rgb = _solid_fill_rgb(shape)
        if rgb is None:
            continue
        inside = (
            shape.left <= cx <= shape.left + shape.width
            and shape.top <= cy <= shape.top + shape.height
        )
        if not inside:
            continue
        area = shape.width * shape.height
        if best is None or area < best[0]:
            best = (area, rgb)
    return best[1] if best else None


_INDEX_RE = re.compile(r"\d{1,3}")
_YEAR_RE = re.compile(r"20\d{2}")


def _is_accent(text: str, size_pt: float) -> bool:
    """序号、指标大数字、每页一枚小标签保留强调色，其余一律压成灰阶。"""
    if text == "N=?" or text in ACCENT_EYEBROWS or _YEAR_RE.fullmatch(text):
        return True
    return bool(_INDEX_RE.fullmatch(text)) and size_pt >= INDEX_MIN_FONT_PT


def neutralize_colors(prs) -> None:
    """把大面积彩色块与彩字压成灰阶，只给少数小字留强调色。"""
    for slide in prs.slides:
        for shape in _iter_shapes(slide.shapes):
            rgb = _solid_fill_rgb(shape)
            if rgb in NEUTRAL_FILL_MAP:
                shape.fill.fore_color.rgb = RGBColor.from_string(NEUTRAL_FILL_MAP[rgb])

    # 四栏卡是重点展示图，底色缺失说明母版变了，必须报错而不是静默跳过
    for index in CARD_SLIDE_INDEXES:
        found = {_solid_fill_rgb(shape) for shape in prs.slides[index].shapes}
        missing = [fill for fill in CARD_FILLS if NEUTRAL_FILL_MAP[fill] not in found]
        if missing:
            raise RuntimeError(f"第 {index + 1} 页未找到四栏卡底色 {missing}")

    for slide in prs.slides:
        # 只用顶层形状求底色：组内坐标与幻灯片坐标不同系，混用会算错位置
        shapes = list(slide.shapes)
        for shape in shapes:
            backdrop = _backdrop_rgb(shapes, shape)
            on_light = backdrop is not None and _relative_luminance(backdrop) > 0.5
            # 页眉标识等文字成组出现，组内子形状沿用整组的底色判断
            for node in _iter_shapes([shape]):
                if not getattr(node, "has_text_frame", False):
                    continue
                if not node.text_frame.text.strip():
                    continue
                for run in _iter_runs(node):
                    text = run.text.strip()
                    if not text:
                        continue
                    size = run.font.size.pt if run.font.size else 0.0
                    if _is_accent(text, size):
                        color = ACCENT
                    elif on_light:
                        color = NEUTRAL_TEXT_DARK
                    elif size >= TITLE_MIN_FONT_PT:
                        color = NEUTRAL_TEXT_LIGHT
                    else:
                        color = NEUTRAL_TEXT_BODY
                    run.font.color.rgb = RGBColor.from_string(color)


def _text_width_in(text: str, size_pt: float):
    em = sum(_CHAR_WIDTH_EM.get(ch, 0.6) for ch in text)
    return Inches(em * size_pt / 72)


def fix_metrics_labels(prs) -> None:
    slide = prs.slides[METRICS_SLIDE_INDEX]
    numbers = {}
    for shape in slide.shapes:
        if not shape.has_text_frame:
            continue
        text = shape.text_frame.text.strip()
        if text in METRIC_LABELS and _shape_max_font_pt(shape) == METRIC_NUM_PT:
            numbers[text] = shape

    missing = [text for text in METRIC_LABELS if text not in numbers]
    if missing:
        raise RuntimeError(f"第 {METRICS_SLIDE_INDEX + 1} 页未找到指标数字 {missing}")

    for run in _iter_runs(numbers["N=?"]):
        run.font.color.rgb = RGBColor.from_string(METRIC_ACCENT)

    for text, label_text in METRIC_LABELS.items():
        number = numbers[text]
        left = number.left + _text_width_in(text, METRIC_NUM_PT)
        top = number.top + Emu(int((number.height - METRIC_LABEL_HEIGHT) / 2))
        box = slide.shapes.add_textbox(left, top, METRIC_LABEL_WIDTH, METRIC_LABEL_HEIGHT)
        frame = box.text_frame
        frame.word_wrap = False
        frame.margin_left = 0
        frame.margin_right = 0
        frame.margin_top = 0
        frame.margin_bottom = 0
        paragraph = frame.paragraphs[0]
        paragraph.alignment = PP_ALIGN.LEFT
        run = paragraph.add_run()
        run.text = label_text
        run.font.size = Pt(METRIC_LABEL_PT)
        run.font.name = "MiSans VF Light"
        run.font.color.rgb = RGBColor.from_string(METRIC_LABEL_COLOR)


def add_measured_metrics(prs) -> None:
    """在指标页三条横带里分别加乙组（已实测）数字，与甲组 N=? 明确分开。"""
    slide = prs.slides[METRICS_SLIDE_INDEX]
    for top, height, paragraphs in MEASURED_BOXES:
        box = slide.shapes.add_textbox(MEASURED_LEFT, top, MEASURED_WIDTH, height)
        frame = box.text_frame
        frame.word_wrap = True
        frame.margin_left = 0
        frame.margin_right = 0
        frame.margin_top = 0
        frame.margin_bottom = 0
        frame.vertical_anchor = MSO_ANCHOR.TOP
        for index, (size_pt, base_color, parts) in enumerate(paragraphs):
            paragraph = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
            paragraph.alignment = PP_ALIGN.LEFT
            paragraph.line_spacing = 1.0
            paragraph.space_before = Pt(0 if index == 0 else 2)
            paragraph.space_after = Pt(0)
            for text, accent in parts:
                run = paragraph.add_run()
                run.text = text
                run.font.size = Pt(size_pt)
                run.font.name = MEASURED_FONT
                run.font.color.rgb = RGBColor.from_string(ACCENT if accent else base_color)


def _save(prs, dst: Path) -> None:
    try:
        prs.save(dst)
    except PermissionError:
        # PowerPoint 占用产物时留下 ~$ 锁文件；清掉后重试一次，仍失败则抛出
        for lock in Path.cwd().glob("~$*.pptx"):
            lock.unlink(missing_ok=True)
        prs.save(dst)


def main() -> int:
    src = Path(SRC)
    if not src.is_file():
        raise FileNotFoundError(f"找不到母版文件: {src}")

    dst = _dst_path()
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)

    prs = Presentation(str(dst))
    if len(prs.slides) != SLIDE_COUNT:
        raise RuntimeError(f"母版页数应为 {SLIDE_COUNT}，实际 {len(prs.slides)}")

    fix_chapter_number(prs)
    neutralize_colors(prs)
    add_page_numbers(prs)
    fix_metrics_labels(prs)
    add_measured_metrics(prs)

    _save(prs, dst)
    print(f"已生成 {dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())