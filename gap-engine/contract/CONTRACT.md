# gap-engine 契约（C-SCHEMA@1 / C-PRIORITY@1 / C-TRACE@1 / C-MATCHER@4 / C-PROBER@5 / C-PIPELINE@5 / C-EXTRACTOR@4/@5 / C-RENDERER@7 / C-DEMO@2 / C-LLM@1）

> 本文件是人可读镜像，实现以 `src/gap_engine/` 与 `demo/` 为准。每个 AI 会话开始前先读这十二句。

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
12. AI 只做推演：LLM 不进三态、不产定位、不写 `Verdict` 任何字段，只写 `--out` 指向的独立产物；`--llm` 为显式开关，未配置凭据时产物必须标注「未调用 AI」。

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
| C-DEMO@2 | `demo/source.py`（新增）+ `demo/app.py` | `extract_zip` / `clone_github` + 四个上限常量；三种输入方式与 UI 约束 |
| C-LLM@1 | `src/gap_engine/llm.py` + `advice.py` + `specjson.py` + `progress.py` + `cli.py` | `LlmProvider` / `HttpLlm` / `load_provider` / `as_llm_fn`；`advice_targets` / `render_advice`；`build_spec_document` / `write_spec_json` / `load_spec_json`；`LABEL_CRITERIA` / `LABEL_ADVICE` / `TEXT_MAX_CHARS` / `ProgressEvent` / `ProgressFn` / `stderr_progress` / `resolve_progress`；`gap parse-spec` / `gap advise` 的 `--progress` / `--no-progress` |

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

## demo 输入源（C-DEMO@2）

- **三种输入**：服务器路径 / 上传 zip / GitHub URL。全部在 `tempfile.TemporaryDirectory()` 内处理，请求结束即清理，不写进程 cwd、不写仓库目录。
- **zip 约束**：上传 ≤ 20 MB、解压累计 ≤ 200 MB、条目 ≤ 2000；拒绝含 `..` 的成员、绝对路径、盘符、符号链接；解压后若只有一个顶层目录则自动下钻。
- **clone 约束**：只接受 `https://github.com/<owner>/<repo>` 形式；`git clone --depth 1`，超时 120 s，`GIT_TERMINAL_PROMPT=0`；**禁止 `shell=True`**，URL 不得拼进字符串命令；超时映射为 `TimeoutError`，非零返回码映射为 `ValueError`。
- **UI 约束**：`st.text_input` 共 3 个（服务器路径、GitHub URL、需求清单）；异常只捕获 `(OSError, ValueError)`，禁止 `except Exception`。
- 输入源变化**不改变**三态判定与判定域规则：仍然是「识别七类、只判四类」，`architecture` / `scale` / `security` 始终 `out_of_scope`。

## AI 推演（C-LLM@1）

- **零依赖**：`pyproject.toml` 的 `dependencies = []` 保持不变；provider 只用标准库 `urllib.request` POST `{base_url}/chat/completions`，`llm.py` 只 import `json` / `os` / `urllib.error` / `urllib.request` / `dataclasses` / `typing`。
- **`--llm` 显式开关**：`gap parse-spec` 与 `gap advise` 的 `--llm` 默认关闭；即使环境里有 `GAP_LLM_API_KEY`，未传 `--llm` 也**不发起任何网络请求**。凭据只从 `GAP_LLM_API_KEY` / `GAP_LLM_BASE_URL` / `GAP_LLM_MODEL` / `GAP_LLM_TIMEOUT` 读，超时解析失败回落 `30.0` 并钳制到 `(0, 120]`。
- **无凭据标注「未调用 AI」**：`load_provider()` 读不到非空 key 时返回 `None`（不返回空 provider、不发起请求）；推演产物固定写 `- 未调用 AI（未配置 GAP_LLM_API_KEY 或未加 --llm），本批次无推演建议。`，stderr 同时提示 `未配置 GAP_LLM_API_KEY，已降级为规则解析`。
- **AI 不进三态、不产定位**：产物里每条建议带固定标识 `> AI 推演（非证据，不产生定位，不改变三态结论）`；AI 输出不得写入 `Verdict` 的 `status` / `locator` / `evidence_ids` / `search_trace` / `reason` / `fix`，不得产生 `file:line`，不得引入第四种状态。`advise` 只挑 `status is no_evidence` 且 `out_of_scope is False` 的条目，按 `claim.id` 升序最多 `ADVICE_LIMIT = 10` 条；prompt 只含需求原文、已执行的探测项名称、已扫处数合计与缺口标签，**不含源码内容、文件路径、`Locator`**。
- **需求清单固化（`gap-spec@1`）**：`gap parse-spec` 落盘 `{"schema": "gap-spec@1", "source", "provider", "items", "dropped"}`（键名与顺序固定，`indent=2`、`ensure_ascii=False`、末尾单换行）；`items` 的 `text` / `line` / `decidable` 唯一来源是规则解析 `spec.parse_spec`，LLM 不得增删条目、不得改 `decidable`，也不碰 `Verdict`。
- **B 段：为不可判定条目生成可验收判据**：`provider` 非空时，对每条 `decidable is False` 的条目调用一次 `provider.complete(CRITERIA_PROMPT.format(text=item.text))`，取返回值 `strip()` 后的首个非空行并截断到 `CRITERIA_MAX_CHARS = 200` 字符，非空则覆盖该条 `suggestion`；空串或异常保留规则值（`suggestion` 绝不变空）。`decidable is True` 的条目**一律零调用**——验收基准是 fx-spec 的 5 条里恰有 1 条「高性能」不可判定，故恰好 1 次调用。`prompt` 只含需求原文，**不含仓库文件路径、源码、`Locator`、探测项名**。判据随 JSON 一起落盘固化，后续对账只读该文件、不再重算判据，因此同一份清单两次解析逐字节一致；`load_spec_json` 回读时校验 `schema` 与每项类型，**不读 `provider`、不发起任何调用**。
- **失败一律降级**：超时、非 2xx、JSON 非法、结构缺字段、`content` 非字符串，`complete` 一律返回空串，不重试、不抛异常；`as_llm_fn(None)` 返回 `None`，对账主链路不中断。
- **产物边界**：两个子命令的产物路径只由 `--out` 决定，**六份 `reports/fx-*.md` 逐字不变**（`tests/test_fixtures.py` 守卫），既有 `analyze` / `questions` / `spec` / `score` 的参数与输出一字不改。- **进度只走 stderr（progress@1 / specjson@3 / advice@2 / cli@2）**：`progress.py` 对外提供 `LABEL_CRITERIA = "生成判据"` / `LABEL_ADVICE = "生成建议"` / `TEXT_MAX_CHARS = 40` / `ProgressEvent` / `ProgressFn` / `stderr_progress` / `resolve_progress`，只写调用方传入的 stream，**不写 stdout、不写文件、不 import `specjson` / `advice` / `cli`**。`build_spec_document` / `write_spec_json` / `render_advice` 各增尾随可选参数 `progress: ProgressFn | None = None`，每次模型调用**严格成对**发一次 `start`（`seconds` 恒 `0.0`）与一次 `done`（`seconds` 为 `time.perf_counter()` 差值）；`total` 分别为不可判定条目数与 `len(advice_targets(analysis))`，`label` 分别恒为 `LABEL_CRITERIA` / `LABEL_ADVICE`。`provider is None` 或 `progress is None` 时**零事件**，`items` 内容、顺序与产物字节不变。渲染格式固定：`start` 写 `[{index}/{total}] {label}：{text} ...` 且不换行，`done` 写 `\r[{index}/{total}] {label}：{text} ... {seconds:.2f}s\n`，两次都 `flush()`；`text` 超过 `TEXT_MAX_CHARS` 截断并补 `…`。
- **进度开关三态**：`parse-spec` 与 `advise` 提供 `--progress` / `--no-progress`（`argparse.BooleanOptionalAction`，`dest="progress"`，`default=None`）。`resolve_progress(None, stream)` 按 `stream.isatty()` 自动判定——交互终端显示、管道/重定向/CI 静默；`True` 无条件显示、`False` 静默。**stdout 输出不变**：`parse-spec` 仍只有 `spec: {path}`，`advise` 仍只有 `advice: {path}`；退出码、降级提示与产物路径规则与 @1 一致。