# gap-engine 契约十一句（C-SCHEMA@1 / C-PRIORITY@1 / C-TRACE@1 / C-MATCHER@4 / C-PROBER@5 / C-PIPELINE@5 / C-EXTRACTOR@4/@5 / C-RENDERER@7）

> 本文件是人可读镜像，实现以 `src/gap_engine/` 为准。每个 AI 会话开始前先读这十一句。

1. 状态只有三种：`supported` / `contradicted` / `no_evidence`，不存在第四种。
2. 敢说"支持"或"反对"，就必须给出一个可点击定位（`file:line`）；给不出，只能是 `no_evidence`。
3. 判 `no_evidence` 且一处都没查过（`search_trace` 为空）时，`coverage` 必须是 `none`。
4. 字段名与《施工图-对账引擎》§1.2 完全一致，不设别名，序列化 key 与原字段同名。
5. 枚举值即 JSON 值；禁止在其它文件里重复定义同名字符串常量。
6. 不变量在构造期强制：非法 Verdict 抛 `ValueError`，消息前缀固定为 `verdict.invariant:`。
7. 不做隐式修正：不自动补 locator，不自动降级 status，不返回错误码。
8. `question_priority` 只由 `(status, confidence)` 决定，取值 0–10 的整数。
9. 同分按 `claim_id` 升序，且不引入任何第二排序键。
10. 报告里的"查过 N 类 M 处"只能由 `trace.summarize` / `trace.headline` 产出，禁止调用方自算或拼字符串；`out_of_scope=True` 的 claim 不进任何比率分母。
11. `Verdict.rounds` 是**实际跑过的检索轮数**，不是配置值：`max_rounds` 只被钳制到 `1..3`；某类没有备用假设时恒为 `1`，有备用假设但第 2 轮也没找到证据时如实写 `2`。轮次只升不降，证据按 `evidence.id` 去重后跨轮累加，`search_trace` 同样累加。

## 对应契约

| 契约 | 提供方 | 对外符号 |
| --- | --- | --- |
| C-SCHEMA@1 | `src/gap_engine/schema.py` | `Claim` / `Evidence` / `SearchProbe` / `Verdict` / `Locator`、6 个枚举、`JUDGEABLE_TYPES`、`is_judgeable`、`to_dict` |
| C-PRIORITY@1 | `src/gap_engine/priority.py` | `STATUS_WEIGHT` / `CONFIDENCE_WEIGHT` / `compute_question_priority` / `sort_key` |
| C-TRACE@1 | `src/gap_engine/trace.py` | `TraceSummary` / `summarize` / `headline` |
| C-PROBER@5 | `src/gap_engine/prober.py` | `PLAN` / `ALTERNATE_PLANS` / `plan(claim, round=1)` / `run(claim, index, round=1)` |
| C-MATCHER@4 | `src/gap_engine/matcher.py` | `judge`、`claim_terms`、`CONTRADICTED_QUESTION_TEMPLATE`（`contradicted` 判定） |
| C-PIPELINE@5 | `src/gap_engine/pipeline.py` | `analyze_repo` / `analyze_spec` 的 `max_rounds` 与挑战循环（`_judge_one`：只有 `no_evidence` 进第 2 轮） |
| C-EXTRACTOR@4 | `src/gap_engine/extractors/artifact.py` | `extract`（`kind="bench"`、`strength="medium"`、`CAP=40`） |
| C-EXTRACTOR@5 | `src/gap_engine/extractors/negation.py` | `NEGATION_MARKERS` / `extract`（显式否定声明） |
| C-RENDERER@7 | `src/gap_engine/renderer.py` | `render` 的 `结论：` 三态文案、`换假设：{rounds} 轮` 行、局限段措辞 |

## Challenger（规则版）

- **已实现的是检索层换假设重搜**：`no_evidence` 的条目进第 2 轮，换查"结果/产物文件"（`performance` / `concurrency` → 压测结果文件，`testing` → 覆盖率产物），新证据能落到 `file:line` 才允许升为 `supported`。
- 边界：轮次表驱动、有限可枚举（每类至多 1 个备用假设，`max_rounds` 硬上限 3），**不做 LLM 反证、不做多 Agent 对话**——否则同一仓库两次跑轨迹不同，`search_trace` 就失去可复核的意义。
- 只升不降：第 1 轮已 `supported` **或已 `contradicted`** 的直接返回，只有 `no_evidence` 进第 2 轮；认为误报只能提交证据复核。
- 产物证据：`reports/fx-challenge.md` 的 `换假设：2 轮（第 1 轮查预设来源，其后换假设重搜）` 与 `loadtest/report.log:2`。

## contradicted（已实现）

- **三条判定条件**（缺一不可）：① 证据含**显式否定声明**（`extractors/negation.py` 的 `NEGATION_MARKERS`，不在 matcher 里另抄一份）；② 与需求关键词相关（`matcher.claim_terms`，与需求无关的否定不算）；③ 能贴出 `file:line`（锚点 `line is None` 时不判 `contradicted`，降回原流程）。
- **反证优先于支持证据**：同一条既有支持痕迹又是否定声明时仍判 `contradicted`，`reason` 写「代码里有反证：…（另有 k 处支持痕迹，被反证推翻）」。
- **不进挑战循环**：`contradicted` 与 `supported` 都在第 1 轮返回，`Verdict.rounds` 恒为 `1`；只有 `no_evidence` 进第 2 轮。
- 产物证据：`reports/fx-contradicted.md` 的 `结论：代码里有反证，与要求不一致` 与 `- 定位：app.py:9`。