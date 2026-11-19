"""初赛 PPT 视觉定稿生成脚本。

按 ``ppt/PPT大纲.md`` 的 15 页结构生成 16:9 深色版演示稿，输出
``ppt/对账引擎-初赛.pptx``。只依赖 python-pptx，不影响 gap-engine 运行时零依赖。

数字纪律：所有指标一律 ``N=?``，页脚重复「禁止估算」提示。
"""

from __future__ import annotations

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

OUT = Path(__file__).resolve().parent / "对账引擎-初赛.pptx"

W, H = Inches(13.333), Inches(7.5)
BG = RGBColor(0x0F, 0x1B, 0x2D)
FG = RGBColor(0xEC, 0xF2, 0xF8)
MUTED = RGBColor(0x8F, 0xA3, 0xB8)
ACCENT = RGBColor(0x2D, 0xD4, 0xBF)
WARN = RGBColor(0xFF, 0xB4, 0x5C)
FONT = "微软雅黑"

MARGIN = Inches(0.85)
BODY_TOP = Inches(1.75)
BODY_W = W - MARGIN * 2


def _blank(prs: Presentation):
    return prs.slides.add_slide(prs.slide_layouts[6])


def _rect(slide, left, top, width, height, color, alpha=None):
    shape = slide.shapes.add_shape(1, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()
    if alpha is not None:
        shape.fill.fore_color._xFill.srgbClr.append(
            shape.fill.fore_color._xFill.srgbClr.makeelement(
                "{http://schemas.openxmlformats.org/drawingml/2006/main}alpha",
                {"val": str(int(alpha * 100000))},
            )
        )
    return shape


def _text(slide, left, top, width, height, text, size, color=FG, bold=False, align=PP_ALIGN.LEFT):
    box = slide.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.TOP
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    run.font.name = FONT
    return box


def _page(prs, num, kicker, title, bullets, cite, note=None):
    slide = _blank(prs)
    _rect(slide, 0, 0, W, H, BG)
    _rect(slide, 0, 0, Inches(0.18), H, ACCENT)

    _text(slide, MARGIN, Inches(0.52), Inches(8), Inches(0.4), kicker, 18, ACCENT, bold=True)
    _text(slide, MARGIN, Inches(0.95), BODY_W, Inches(0.8), title, 34, FG, bold=True)
    _rect(slide, MARGIN, Inches(1.62), Inches(1.5), Emu(38100), ACCENT)

    box = slide.shapes.add_textbox(MARGIN, BODY_TOP, BODY_W, Inches(4.5))
    tf = box.text_frame
    tf.word_wrap = True
    first = True
    for item in bullets:
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.space_after = Pt(14)
        run = p.add_run()
        run.text = f"·  {item}"
        run.font.size = Pt(19)
        run.font.color.rgb = FG
        run.font.name = FONT

    if note:
        nb = slide.shapes.add_textbox(MARGIN, Inches(6.05), BODY_W, Inches(0.5))
        ntf = nb.text_frame
        ntf.word_wrap = True
        nrun = ntf.paragraphs[0].add_run()
        nrun.text = note
        nrun.font.size = Pt(18)
        nrun.font.bold = True
        nrun.font.color.rgb = WARN
        nrun.font.name = FONT

    _text(slide, MARGIN, Inches(6.78), Inches(9.2), Inches(0.4), f"引用产物：{cite}", 12, MUTED)
    _text(slide, W - Inches(1.55), Inches(6.78), Inches(0.7), Inches(0.4), f"{num:02d}", 12, MUTED, align=PP_ALIGN.RIGHT)
    return slide


def build() -> Path:
    prs = Presentation()
    prs.slide_width, prs.slide_height = W, H

    # P1 封面
    s = _blank(prs)
    _rect(s, 0, 0, W, H, BG)
    _rect(s, 0, 0, W, Inches(0.22), ACCENT)
    _text(s, MARGIN, Inches(1.9), Inches(11.5), Inches(1.0),
          "对账引擎（Gap Engine）", 52, FG, bold=True)
    _text(s, MARGIN, Inches(3.0), Inches(11.5), Inches(1.2),
          "要求做的，代码里到底有没有", 30, ACCENT, bold=True)
    _text(s, MARGIN, Inches(4.1), Inches(11.0), Inches(1.0),
          "给一份需求清单 + 一个代码仓库，输出「要求做的」和「代码里有的」之间的缺口", 20, FG)
    _rect(s, MARGIN, Inches(5.15), Inches(2.2), Emu(38100), ACCENT)
    _text(s, MARGIN, Inches(5.45), Inches(11.0), Inches(0.45),
          "不是判官，是双方共用的尺子 ——「可信度的 CI」", 20, MUTED)
    _text(s, MARGIN, Inches(6.15), Inches(11.0), Inches(0.9),
          "队伍：eon ego　｜　初赛：2 人 / D0–D6（2026-11-15 → 11-20）", 18, MUTED)
    _text(s, MARGIN, Inches(6.62), Inches(11.0), Inches(0.5),
          "指标待 5 份需求清单回执后填入（N=?），禁止估算", 18, WARN, bold=True)

    # P2 场景背景
    _page(prs, 2, "创新性与价值", "同一个问题，有两面", [
        "老师 / 大创负责人拿着一份 20 条要求，只能逐条翻代码 —— 要求方核不动",
        "学生简历写「支持 500 并发」，一问压测脚本就沉默 —— 交付方说不清",
        "2025 后声称的生产成本塌了：README、简历一分钟一千字，验证的价值就上来了",
        "这件事在课程设计 / 大创结题 / 外包交付 / 面试 / 开源 README 里重复发生",
        "不问「这段代码写得好不好」，问「要求做的，做了吗，能证明吗」",
    ], "对账引擎/README.md（问题一节）")

    # P3 红海与空位
    _page(prs, 3, "创新性与价值", "红海与空位：契约二分", [
        "行为契约（OpenAPI / Pact / schemathesis 3,777★）：路径存在、参数类型、响应 schema —— 一条规则能判，我们不碰",
        "能力契约（「支持 500 并发」「P95 < 300ms」「可用性 99.9%」）：需要一组证据，而且不知道该找哪一组 —— 这才是我们的地方",
        "OpenSLO 有 1,542★ 规范与生成生态，验证类工具 0 个；但它是商业方向（用户是大厂 SRE），只进 roadmap",
        "自检口径：一条证据就能判的都不是我们的活；需要一组证据且不知找哪一组的，都是我们的活",
        "代码里已落地：分类器认七类，判定域只开四类",
    ], "相关工作.md §五–§六；schema.py")

    # P4 产品定义
    _page(prs, 4, "技术实现", "产品定义：输入、输出、一条命令", [
        "输入：一份需求清单（Markdown 列表）+ 一个代码仓库",
        "命令：gap spec <repo> --spec <requirements.md>（副模式 gap analyze <repo> 读 README 自我声称）",
        "输出：① 需求可判定性预检 ② 这个项目实际是什么 ③ 需求 ↔ 证据对照表 ④ 会被追问的问题 ⑤ 最小补齐行动（⑥ 可直接应用的补齐物属 roadmap）",
        "双方都能跑：交差方看「我还差什么」，验收方看「他还差什么」，同一段代码、同一套轨迹",
        "只读仓库：不执行、不导入被测代码",
    ], "reports/fx-spec.md；readme/run.md")

    # P5 功能架构
    _page(prs, 5, "技术实现", "一次对账的数据流", [
        "入站适配（Markdown → Claim）→ Claimer（抽条目 + 七类分类）→ Prober（9 个规则抽取器）→ Matcher（三态）→ Renderer（报告）",
        "三态只有 supported / contradicted / no_evidence —— 没有第四态；「部分支持」只是 no_evidence 的措辞",
        "证据单元带 file:line；搜不到也要输出 search_trace（查过哪几类、扫过几处、命中几处）",
        "Agent 口径：7 个位 = 5 已实现（Claimer / Prober / Matcher / Challenger 规则版 / Renderer）+ 2 roadmap（Healer / Verifier）",
        "真值由需求提出人判（对 / 错 / 说不清），不是我们自己标",
    ], "施工图-对账引擎.md §0–§1.6")

    # P6 亮点①
    _page(prs, 6, "核心亮点 ①", "输出 ≠ 证据", [
        "每条结论必须给两样之一：断言 → file:line；没找到 → search_trace",
        "什么都没查到的也输出，标 coverage=none，明确不作为证据 —— 沉默会让用户以为这条没问题",
        "报告原话：「查过 6 类 15 处，未找到」—— 这是证据地图，不是「你没做」",
        "三条纪律：no_evidence 永远是「我没找到」；一条 claim 只有一个断言；contradicted 必须贴得出反证",
        "audit effort 可计算：类数 = 探测项数，处数 = sum(scanned)",
    ], "reports/fx-spec.md（「支持 500 并发用户」条目）")

    # P7 亮点②
    _page(prs, 7, "核心亮点 ②", "判据外置，翻不出来就拒答", [
        "可判定的前提是判据存在且外置：声称自带阈值 / 需求文档 / OpenSLO target / 事前声明的行业惯例（须标来源）",
        "已实现：把「高性能 / 高效 / 快速」翻成 P95 < 300ms 或 QPS ≥ 500，并在报告里标明「默认判据」",
        "翻不出来的（「架构合理」「美观」）→ 拒绝生成补齐物，标不可判定，给改写建议",
        "这条决定 Healer 的死线：只补观测、不补实现；判据没法外置就不许补",
        "判定域已拓宽到 21 项 / 9 组（合规、隐私、审计、运维、隔离、可观测、国际化、无障碍等）",
    ], "src/gap_engine/spec.py；reports/fx-spec.md（预检段）")

    # P8 亮点③
    _page(prs, 8, "核心亮点 ③", "双方共用的尺子 = 可信度的 CI", [
        "A 查 B 时 B 会防御、数据拿不到；两人共用一把尺子，争议就变成「看尺子」",
        "CI 不保证没 bug，只保证结果可复现；我们不保证判得对，只保证轨迹可核",
        "CI 会漏，没人因此不用 CI —— 它的价值是给所有人一个共同的、可复现的事实",
        "前提是边界公开：哪些判不了、说不清率多少、哪类会漏 —— 公开边界的工具，错了也在预期内",
        "所以 search_trace 和「说不清率」不是诚实姿态，是产品设计",
    ], "对账引擎/README.md（立场节）；对抗自查.md")

    # P9 技术实现
    _page(prs, 9, "技术实现 / 工程质量", "能用规则判的，绝不给 LLM", [
        "路由 / 依赖 / 测试文件 / 锁 / 压测产物 / 符号，全走规则，定位率天然接近 100%",
        "AI 只承担唯一开放的那一步：「要证明这句话，需要查什么？」（推演 + 换假设重搜，上限 3 轮；默认关闭）",
        "判定域只开 performance / concurrency / feature / testing；其余标 out_of_scope，不扩类也不硬判",
        "可复现：pip install -e gap-engine → gap --help → 一条命令出报告；525 项测试全绿；干净 venv 已实跑验证",
        "匿名化：不含 .env / API Key / 第三方项目原始代码",
    ], "tests/；readme/install.md、readme/run.md")

    # P10 码道应用说明（独立页）
    _page(prs, 10, "码道使用深度", "码道在项目里具体做了什么", [
        "需求分析：需求清单可判定性预检（哪些要求根本没法验收）用码道对话产出规则，落到 spec.py",
        "生成：9 个抽取器、三态判定、报告渲染、CLI 子命令，按 plan → 契约 → 实现推进，每步有会话记录",
        "测试：闸门式验收，每批改动必须过 pytest；失败用例原样回灌码道定位",
        "排错：报告口径类 bug（如「未覆盖」被渲染成沉默）用码道做差异定位，改完补回归用例",
        "留痕：codearts_proof/daily/D0–D6 连续记录 + 截图 + git log，每天归档，不做事后补造",
    ], "codearts_proof/（daily / 截图）；tests/")

    # P11 指标
    _page(prs, 11, "技术实现", "指标：数字全部占位", [
        "样本：5 份老师 / 大创需求清单 × 各 5 条 = 25 条，对 5 个项目代码；由需求提出人本人判定",
        "认可率 N=?（目标 ≥70%，分母 = 对 + 错，说不清不计）　｜　定位率 N=?（目标 ≥90%，分母 = 断言型结论）",
        "漏报率 N=?（≤20%）　｜　误报率 N=?（≤10%）—— 两个方向相反，必须分开报",
        "无法证伪异议率 / 说不清率 / 未覆盖率 均 N=?（如实报，不设目标）",
        "普遍性：默认先验值；已实测 10 个公开仓库（可判定声称 N=3：performance 1 + feature 2），先验与实测不混用",
    ], "reports/prevalence.json、prevalence-sample.md；施工图 §2.6",
        note="所有 N=?：待 5 份需求清单回执后填入，禁止估算；有效回执不是 25 就如实写")

    # P12 我们不能证明什么
    _page(prs, 12, "边界页（主动划线）", "我们不能证明什么", [
        "这是 pilot：25 条结论、有效回执 N=?（待回执后填入，禁止估算）",
        "只回答三件事：方法在真实小样本上跑得起来 / 定位率多高 / 错误长什么样",
        "不做显著性声明，不宣称普适准确率；限定 Python / JS、500–5000 行、只判四类条目",
        "不做「全面理解代码」（CodeWiki 1,862★ 等已占位），只做「这代码在干什么」的报告一段",
        "需求清单来源逐份标注；自己反写的不计入样本",
    ], "日程计划-初赛冲刺.md §5；对抗自查.md")

    # P13 相关工作
    _page(prs, 13, "创新性与价值", "前车之鉴：不是路死了，是站错了边", [
        "简历验证有人做过，全死了：SkillTruth 4★（退化成 AI 面试）/ labora 2★（退化成简历润色）/ Ada 1★（做太深做不完）",
        "死因：站在「查」的立场 → 被查的人不配合 → 数据拿不到",
        "与 DocPrism（98% → 14%）的区别：比的是项目级声称 vs 整仓证据，要先推演该去哪找，且只报「我没找到证据」",
        "与 traceability 工具（doorstop 697★ / duvet 172★）的区别：它们靠人维护链接，我们靠搜索找证据并交出轨迹",
        "与 schemathesis / Pact 的区别：行为契约我们不碰，只做能力契约",
    ], "相关工作.md")

    # P14 roadmap
    _page(prs, 14, "roadmap（不许写成已完成）", "下一阶段：已经做到哪，还没做到哪", [
        "Challenger 已实现，形态是规则版：换假设重搜 + 只认显式否定反证；独立的对抗复核 Agent 属下一阶段",
        "Healer / Verifier 属 roadmap：只补观测不补实现；补齐物 = locustfile.py + CRITERIA.md + run.sh + 原始日志",
        "出站 SARIF（技术上约 1 天，语义上要先解决：缺证据 ≠ 缺陷）属 roadmap；入站 OpenSLO 是商业方向，非比赛方向",
        "gap explain <问题> 需要调用图，不是现有索引的副产物，属 roadmap",
        "部署：本地一键运行 + 录屏；公网实例为预览加分项，非必需",
    ], "施工图 §1.6–§1.7；对账引擎/README.md")

    # P15 结尾
    s = _blank(prs)
    _rect(s, 0, 0, W, H, BG)
    _rect(s, 0, 0, W, Inches(0.22), ACCENT)
    _text(s, MARGIN, Inches(1.75), Inches(11.4), Inches(1.4),
          "能证明「要求做的，真的做了」", 42, FG, bold=True)
    _text(s, MARGIN, Inches(3.0), Inches(11.4), Inches(1.4),
          "做不到的那几条，它让你看见，而不是替你圆", 30, ACCENT, bold=True)
    _rect(s, MARGIN, Inches(4.25), Inches(2.2), Emu(38100), ACCENT)
    _text(s, MARGIN, Inches(4.55), Inches(11.4), Inches(0.45),
          "不用读代码，也知道该读哪几行（gap explain 属 roadmap）", 19, MUTED)
    _text(s, MARGIN, Inches(5.25), Inches(11.4), Inches(0.45),
          "现场演示：gap spec ...（可现场跑，失败则播视频）", 19, FG)
    _text(s, MARGIN, Inches(5.8), Inches(11.4), Inches(0.45),
          "我们报了漏报率，也报了误报率 —— 两个数字都可以问", 19, WARN, bold=True)
    _text(s, MARGIN, Inches(6.6), Inches(11.4), Inches(0.45),
          "队伍：eon ego　｜　2026-11-20", 18, MUTED)

    prs.save(OUT)
    return OUT


if __name__ == "__main__":
    path = build()
    print(f"ppt: {path}")