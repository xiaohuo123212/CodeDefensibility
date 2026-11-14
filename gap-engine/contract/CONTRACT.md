# gap-engine 契约十一句（C-SCHEMA@1 / C-PRIORITY@1 / C-TRACE@1 / C-PROBER@5 / C-PIPELINE@4 / C-RENDERER@6 / C-EXTRACTOR@4）

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
| C-PIPELINE@4 | `src/gap_engine/pipeline.py` | `analyze_repo` / `analyze_spec` 的 `max_rounds` 与挑战循环（`_judge_one`） |
| C-EXTRACTOR@4 | `src/gap_engine/extractors/artifact.py` | `extract`（`kind="bench"`、`strength="medium"`、`CAP=40`） |
| C-RENDERER@6 | `src/gap_engine/renderer.py` | 逐条段的 `换假设：{rounds} 轮` 行与局限段的多轮措辞 |

## Challenger（规则版）

- **已实现的是检索层换假设重搜**：`no_evidence` 的条目进第 2 轮，换查"结果/产物文件"（`performance` / `concurrency` → 压测结果文件，`testing` → 覆盖率产物），新证据能落到 `file:line` 才允许升为 `supported`。
- 边界：轮次表驱动、有限可枚举（每类至多 1 个备用假设，`max_rounds` 硬上限 3），**不做 LLM 反证、不做多 Agent 对话**——否则同一仓库两次跑轨迹不同，`search_trace` 就失去可复核的意义。
- 只升不降：第 1 轮已 `supported` 的直接返回，不进循环；认为误报只能提交证据复核。
- 产物证据：`reports/fx-challenge.md` 的 `换假设：2 轮（第 1 轮查预设来源，其后换假设重搜）` 与 `loadtest/report.log:2`。