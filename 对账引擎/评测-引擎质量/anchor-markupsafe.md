# markupsafe 4 条声称的标注结果

真值判定方式：逐条到代码里找实现证据，不采信 README 自述。
需求来源：`markupsafe/README.md:5-9`（正文段）与 `README.md:22-27`（示例注释）。
引擎报告：`spec-markupsafe-v6.md`（`C-MATCHER@10` 产物，与本目录 `spec-markupsafe.md` 逐字相同）。
标注结论：**4 条全部有真实实现**，真值均为 `supported`，真 `contradicted` 为 0 条。
**`C-MATCHER@10` 后不变**：复算结果仍为 supported 1 / no_evidence 1 / 不判定 2（1+1+2=4），与 @9 完全相同，故本文件逐条结论未改。

| # | 声称 | 引擎结论 | 真值 | 判定 | 代码证据 |
|---|---|---|---|---|---|
| 1 | 实现可安全用于 HTML 和 XML 的文本对象 | 不判定（超出判定域：安全类） | supported | 不判定（拒答） | `src/markupsafe/__init__.py:84-118` `class Markup(str)`，docstring 明写「ready to be safely inserted into an HTML or XML document」；`:24-45` `escape()` 返回 `Markup` |
| 2 | 转义特殊含义字符，使其显示为原字符 | no_evidence | supported | 漏报 | `_native.py:1-8` 对 `& > < ' "` 五个字符做实体替换；`__init__.py:39-40` 快路径 `Markup(_escape_inner(s))`；`_speedups.c` 为同语义的 C 加速实现 |
| 3 | 缓解注入攻击，不可信输入可安全展示 | 不判定（超出判定域：安全类） | supported | 不判定（拒答） | `__init__.py:24-33` `escape` docstring「Use this if you need to display text that might contain such characters in HTML」；`:48-61` `escape_silent`；`_native.py:1-8` 实体替换即注入缓解手段 |
| 4 | Markup 是 str 子类，方法参数自动转义 | supported | supported | 正确 | `__init__.py:84` `class Markup(str)`；`:136-140` `__add__`/`:142-146` `__radd__` 对参数 `self.escape`；`:154-165` `__mod__` 用 `_MarkupEscapeHelper` 包裹参数；`:170-171` `join` 映射 `self.escape`；`:323-333` `format`/`format_map` 走 `EscapeFormatter` |

## 统计

| 口径 | 数量 | 占 4 条 |
|---|---|---|
| 有证据（supported） | 1 | 25% |
| 没找到证据（no_evidence） | 1 | 25% |
| 有反证（contradicted） | 0 | 0% |
| 不判定（超出判定域，未进入三态） | 2 | 50% |
| 判对 | 1 | 25% |
| 漏报 | 1 | 25% |
| 误报 | 0 | 0% |

口径定义：判对 =「引擎给出的确定结论且与真值一致」/ 总数；漏报 = 真 supported 判成 `no_evidence`；误报 = 真 supported 判成 `contradicted`；不判定 = 引擎按判定域预检整条拒答，不计入三态，也不计入判对/漏报/误报。

二分类（把「有证据」与「有反证」都算作引擎下了确定判断）：

| 指标 | 计算 | 结果 |
|---|---|---|
| precision | 判对数 / 确定判断数 = 1 / 1 | 100%（样本仅 1 条确定判断，不具统计意义） |
| recall | 判对数 / 真 supported 数 = 1 / 4 | 25% |
| 反证专项 | 真 contradicted 0 条，引擎报出 0 条 | 不适用（无真反证样本） |

## 共同根因分析（1 条漏报 + 2 条超域拒答）

1. **第 2 条漏报：实现是字符替换表，不含「转义」这个词之外的锚点**
   - 真实实现 `_native.py:1-8` 是五条 `.replace()`，`_speedups.c` 是 C 版本；探测词若停在「转义 / escape」以外的表述（如「特殊含义字符」）就匹配不到函数体。引擎报告显示否定声明扫过 27 处、实现扫过 13 处，说明扫描范围够，是相关性打分没把 `_escape_inner` 认成实现。
2. **第 1、3 条被「安全类」整条拒答**
   - 报告第 33、67 行理由均为「安全类需求不在本次判定范围」。这两条是本库的全部卖点，实现就在 `escape()` 与 `Markup` 里。markupsafe 共 4 条声称，2 条被判定域挡掉，等于半个库无法评测。
3. **同一库内判定不一致**
   - 第 1 条（HTML/XML 安全）与第 4 条（Markup/自动转义）指向同一份代码，第 4 条判 `supported`、第 1 条却以「安全」为由不判定。说明判定域预检是按声称措辞的关键词（「安全」）触发的，而不是按实际可验证性，同类实现被两种对待。
4. **纯库项目没有「入口/路由」**（全局性）
   - 报告「未识别到启动入口」，「路由/入口」「依赖声明」两类探测恒为 0，5 类里只有 3 类有效。

## 真 contradicted 说明

本库 4 条声称里**不存在真 `contradicted`**。源码里确有否定声明（`__init__.py:337` 对 `Markup.__html_format__` 的 format_spec 抛 `ValueError("Unsupported format specification for Markup.")`），但它与这 4 条声称无关；引擎没有把它误当反证，这一点是对的。反证识别能力仍未被本样本覆盖。