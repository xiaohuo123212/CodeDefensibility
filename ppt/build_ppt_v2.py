"""从 final.pptx 母版生成比赛定稿 pptx。

每次运行都从 SRC 重新复制覆盖 DST，再做四处定点修正：
章节序号、右下角页码、四栏卡对比度、指标页标签，因此重复执行结果一致。
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Emu, Inches, Pt

SRC: str = r"C:\Users\haoll\Downloads\final.pptx"
DST: str = "ppt/对账引擎-初赛.pptx"

SLIDE_COUNT = 18
CHAPTER_SLIDE_INDEX = 13  # 第 14 页：第四章章节页，序号 004 → 04
CARD_SLIDE_INDEXES = (8, 16)  # 第 9、17 页：四栏卡
METRICS_SLIDE_INDEX = 12  # 第 13 页：指标页

CHAPTER_OLD, CHAPTER_NEW = "004", "04"

PAGE_NUMBER_BOX = (Inches(11.40), Inches(7.02), Inches(1.36), Inches(0.24))
PAGE_NUMBER_COLOR = "C7D1DA"

CARD_COL3_FILL = "0A7F8B"
CARD_COL4_FILL = "12293E"
COL3_TEXT_COLOR = "F4F7FA"
COL4_HEAD_COLOR = "6AD7E5"
COL4_BODY_COLOR = "C7D1DA"
HEAD_MIN_FONT_PT = 16.0

METRIC_LABELS = {"N=?": "认可率", "25": "样本条目", "5": "项目数"}
METRIC_NUM_PT = 40.0
METRIC_ACCENT = "21B8C7"
METRIC_LABEL_PT = 8.88
METRIC_LABEL_COLOR = "C7D1DA"
METRIC_LABEL_WIDTH = Inches(1.2)
METRIC_LABEL_HEIGHT = Inches(0.16)

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


def _contains(outer, inner) -> bool:
    return (
        inner.left >= outer.left
        and inner.top >= outer.top
        and inner.left + inner.width <= outer.left + outer.width
        and inner.top + inner.height <= outer.top + outer.height
    )


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


def fix_card_contrast(prs) -> None:
    for slide_index in CARD_SLIDE_INDEXES:
        slide = prs.slides[slide_index]
        cards = {}
        for shape in slide.shapes:
            fill = _solid_fill_rgb(shape)
            if fill in (CARD_COL3_FILL, CARD_COL4_FILL):
                cards[fill] = shape

        for fill in (CARD_COL3_FILL, CARD_COL4_FILL):
            if fill not in cards:
                raise RuntimeError(f"第 {slide_index + 1} 页未找到底色 {fill} 的栏位")

        for shape in slide.shapes:
            if not shape.has_text_frame or not shape.text_frame.text.strip():
                continue
            for fill, card in cards.items():
                if not _contains(card, shape):
                    continue
                if fill == CARD_COL3_FILL:
                    color = COL3_TEXT_COLOR
                elif _shape_max_font_pt(shape) >= HEAD_MIN_FONT_PT:
                    color = COL4_HEAD_COLOR
                else:
                    color = COL4_BODY_COLOR
                for run in _iter_runs(shape):
                    run.font.color.rgb = RGBColor.from_string(color)
                break


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
    add_page_numbers(prs)
    fix_card_contrast(prs)
    fix_metrics_labels(prs)

    _save(prs, dst)
    print(f"已生成 {dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())