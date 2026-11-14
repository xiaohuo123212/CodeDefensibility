"""C-SCOPE@1 守卫：`contract/scope.md` 的类型集合必须与 `is_judgeable` 完全一致。"""

import re
from pathlib import Path

from gap_engine.schema import ClaimType, is_judgeable

SCOPE_DOC = Path(__file__).resolve().parents[1] / "contract" / "scope.md"

HEAD_SEVEN = "## 七类条目"
HEAD_JUDGE = "## 判定域（下结论的四类）"
HEAD_NON_JUDGE = "## 不判定域（识别但不判的三类）"
HEAD_DEFENSE = "## 答辩口径：识别七类为什么只判四类"

HEADINGS = (HEAD_SEVEN, HEAD_JUDGE, HEAD_NON_JUDGE, HEAD_DEFENSE)

ROW_TYPE = re.compile(r"^\|\s*`([a-z_]+)`\s*\|")
DEFENSE_SENTENCE = "可机械判定 = 有固定抽取路径 + 断言可落到 `file:line` 或可复现的搜索轨迹"


def read_doc() -> str:
    return SCOPE_DOC.read_text(encoding="utf-8")


def sections(text: str) -> dict[str, list[str]]:
    """按二级标题切段；返回标题行 -> 该段正文行列表。"""
    result: dict[str, list[str]] = {}
    current: str | None = None
    for line in text.splitlines():
        if line.startswith("## "):
            current = line.strip()
            result[current] = []
        elif current is not None:
            result[current].append(line)
    return result


def types_in(lines: list[str]) -> list[str]:
    """从表格行首的反引号单元格提取类型值，保持出现顺序。"""
    found = []
    for line in lines:
        match = ROW_TYPE.match(line.strip())
        if match:
            found.append(match.group(1))
    return found


def cells_of(lines: list[str]) -> list[list[str]]:
    """提取以反引号类型值开头的表格数据行单元格（表头与分隔行因不匹配 ROW_TYPE 被跳过）。"""
    rows = []
    for line in lines:
        stripped = line.strip()
        if not ROW_TYPE.match(stripped):
            continue
        rows.append([c.strip() for c in stripped.strip("|").split("|")])
    return rows


def test_doc_exists_with_four_sections():
    assert SCOPE_DOC.is_file(), f"缺少 {SCOPE_DOC}"
    parsed = sections(read_doc())
    for heading in HEADINGS:
        assert heading in parsed, f"scope.md 缺少二级标题：{heading}"


def test_seven_types_listed_verbatim():
    lines = sections(read_doc())[HEAD_SEVEN]
    listed = types_in(lines)
    assert len(listed) == 7, f"「七类条目」应有 7 行，实际 {len(listed)} 行：{listed}"
    assert len(set(listed)) == 7, f"「七类条目」出现重复类型：{listed}"
    assert set(listed) == {t.value for t in ClaimType}, f"七类取值与 ClaimType 不一致：{listed}"


def test_judgeable_set_matches_is_judgeable():
    listed = set(types_in(sections(read_doc())[HEAD_JUDGE]))
    expected = {t.value for t in ClaimType if is_judgeable(t)}
    assert listed == expected, f"判定域 {sorted(listed)} != is_judgeable {sorted(expected)}"


def test_non_judgeable_rows_have_two_reason_columns():
    rows = cells_of(sections(read_doc())[HEAD_NON_JUDGE])
    assert len(rows) == 3, f"「不判定域」应为 3 行，实际 {len(rows)} 行"
    for cells in rows:
        assert len(cells) == 3, f"「不判定域」行应为 3 列：{cells}"
        assert cells[1], f"{cells[0]} 缺少「为什么不下结论」"
        assert cells[2], f"{cells[0]} 缺少「要下结论还缺什么」"


def test_non_judgeable_disjoint_from_judgeable():
    parsed = sections(read_doc())
    judgeable = set(types_in(parsed[HEAD_JUDGE]))
    non_judgeable = {cells[0].strip("`") for cells in cells_of(parsed[HEAD_NON_JUDGE])}
    assert len(non_judgeable) == 3, f"「不判定域」应有 3 个不同类型：{sorted(non_judgeable)}"
    assert not (non_judgeable & judgeable), f"判定域与不判定域有交集：{non_judgeable & judgeable}"
    assert non_judgeable | judgeable == {t.value for t in ClaimType}


def test_defense_paragraph_contains_criterion():
    body = "\n".join(sections(read_doc())[HEAD_DEFENSE])
    assert DEFENSE_SENTENCE in body, "「答辩口径」段缺少判断依据原句"