# gap-engine 契约（C-SCHEMA@1 / C-PRIORITY@1 / C-TRACE@2 / C-INDEX@2/@3/@4 / C-MATCHER@5/@6 / C-PROBER@5/@7/@8 / C-PIPELINE@5/@6/@7 / C-EXTRACTOR@4/@5/@6/@7 / C-RENDERER@7/@8/@9 / C-DEMO@2 / C-LLM@1（specjson@4） / C-SPEC@2/@3）

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
| C-SPEC@2/@3 | `src/gap_engine/spec.py` | `NEEDS_CRITERIA`（21 项领域词表）/ `_needs_criteria`（位置最靠前的命中 key）/ `is_decidable` 三分支（可测量优先）/ `suggestion_for` 接入领域词表兜底判据；@3：`NEEDS_CRITERIA` 追加 `数据隔离`（value 同 `租户隔离`） |
| C-PRIORITY@1 | `src/gap_engine/priority.py` | `STATUS_WEIGHT` / `CONFIDENCE_WEIGHT` / `compute_question_priority` / `sort_key` |
| C-TRACE@2 | `src/gap_engine/trace.py` | `TraceSummary` / `summarize` / `headline`；@2：`distinct_scanned`（按 `(probe, target)` 去重） |
| C-INDEX@2/@3/@4 | `src/gap_engine/index.py` | `SKIP_DIRS` / `SKIP_DIR_PREFIXES` / `IGNORE_FILE` / `TEXT_SUFFIXES` / `RepoIndex`（含 `truncated`）/ `build_index`；@4：`SKIP_DIRS` 追加 `.oss-scanner` |
| C-PROBER@5/@7/@8 | `src/gap_engine/prober.py` | `PLAN` / `ALTERNATE_PLANS` / `plan(claim, round=1)` / `run(claim, index, round=1)` / `CANDIDATE_FILES`；@7：「相关实现」改指 `symbols`、feature 收窄兜底 `claim_terms`；@8：收窄复用 `matcher.mentions` |
| C-MATCHER@5/@6 | `src/gap_engine/matcher.py` | `judge`（feature 分支的相关性兜底）、`feature_terms` / `claim_terms`、`CONTRADICTED_QUESTION_TEMPLATE`（`contradicted` 判定）；@6：`mentions`（ASCII 词边界匹配） |
| C-PIPELINE@5/@6/@7 | `src/gap_engine/pipeline.py` | `analyze_repo` / `analyze_spec` 的 `max_rounds` 与挑战循环（`_judge_one`：只有 `no_evidence` 进第 2 轮）；`_facts` 一句话的入口三分支；@6：`_route_hits` / `_route_files` 与 `_overview` 入口行；@7：`_scope_verdict` 判定域短路 |
| C-EXTRACTOR@4 | `src/gap_engine/extractors/artifact.py` | `extract`（`kind="bench"`、`strength="medium"`、`CAP=40`） |
| C-EXTRACTOR@5 | `src/gap_engine/extractors/negation.py` | `NEGATION_MARKERS` / `extract`（显式否定声明） |
| C-EXTRACTOR@6 | `src/gap_engine/extractors/symbols.py` | `SYMBOL_TOKENS` / `extract`（每文件首个符号行，`kind=code`、`strength=low`） |
| C-EXTRACTOR@7 | `src/gap_engine/extractors/negation.py` + `deps.py` | `_EXCEPTION_GUARD` / `_inside_string_literal`（参数校验型异常消息内的否定词不算反证）；`_requirements_names` 先拼接行尾 `\` 续行 |
| C-RENDERER@7/@8/@9 | `src/gap_engine/renderer.py` | `render` 的 `结论：` 三态文案、`换假设：{rounds} 轮` 行、局限段措辞；@8：`_scope_note` 与「不判定」块；@9：`_dedup_note` 去重口径行 |
| C-DEMO@2 | `demo/source.py`（新增）+ `demo/app.py` | `extract_zip` / `clone_github` + 四个上限常量；三种输入方式与 UI 约束 |
| C-LLM@1 | `src/gap_engine/llm.py` + `advice.py` + `specjson.py` + `progress.py` + `cli.py` | `LlmProvider` / `HttpLlm` / `load_provider` / `as_llm_fn`；`advice_targets` / `render_advice`；`build_spec_document` / `write_spec_json` / `load_spec_json`；`LABEL_CRITERIA` / `LABEL_ADVICE` / `TEXT_MAX_CHARS` / `ProgressEvent` / `ProgressFn` / `stderr_progress` / `resolve_progress`；`gap parse-spec` / `gap advise` 的 `--progress` / `--no-progress`；specjson@4：`_CRITERIA_CHECK_RE` 与 `_criteria_for` 只采纳含量化阈值或 `file:` 定位的模型返回值 |

## 索引扩表与截断（C-INDEX@2/@3）

- **归档目录按目录名精确排除**：`SKIP_DIRS` 在既有项之外追加 `_archive` / `_archived` / `archive` / `_old` / `old` / `deprecated`，匹配的是**目录名全等**（不做子串匹配），避免误伤名为 `archive_specs.py` 这类正常文件或含该子串的正常包。
- **C/C++ 头源文件纳入索引**：`TEXT_SUFFIXES` 追加 `.c` / `.h` / `.cc` / `.cpp` / `.cxx` / `.hpp` / `.hh` / `.hxx`。**仅纳入索引，不承诺语义抽取**：这些文件进入索引只意味着会被读取与扫描，`Evidence` 仍取决于既有抽取器是否命中。
- **截断标记**：`RepoIndex` 新增带默认值 `False` 的 `truncated`，`build_index` 按 `bool(pending) or len(found) > max_files` 计算。两个条件缺一不可——外层 `while` 受 `max_files` 约束，内层按目录遍历不受约束，单目录超额时 `pending` 已空，只有 `len(found) > max_files` 能捕捉；`len(found) == max_files` 且无剩余文件时必须为 `False`，故不得用 `>=` 单独判定。
- `truncated` 为 `True` 时 `files` 仍是排序后取前 `max_files`，排序键 `relative_to(root).as_posix()` 与截断顺序不变；`rel` / `read` / `text` / `by_suffix` / `line_of` 语义一字不改，既有调用方不传 `truncated` 仍可用。

## 生成目录排除与 `.ignore`（C-INDEX@3）

- **目录名比较统一小写归一**：`build_index` 判定目录时用 `entry.name.lower() in SKIP_DIRS`，并给 `SKIP_DIRS` 追加 `cmakefiles`。此前是大小写敏感全等匹配，`CMakeFiles/` 因此漏网。
- **生成目录按前缀排除**：新增 `SKIP_DIR_PREFIXES = ("build-", "cmake-build-")`，`entry.name.lower().startswith(SKIP_DIR_PREFIXES)` 命中即整棵剪掉，覆盖 `build-cmake/`、`cmake-build-debug/`、`cmake-build-release/`。**故意不收录** `out`（常是正常包名）与 `.cmake`（普通目录名），二者若要排除由仓库自己的 `.ignore` 声明。
- **仓库根 `.ignore` 声明排除**：常量 `IGNORE_FILE = ".ignore"`。`build_index` 在遍历前读取 `root/.ignore`；文件不存在或不可读时视为空，行为与 `C-INDEX@2` 完全一致。逐行 `strip()` 后跳过空行与 `#` 开头的注释行，末位 `/` 去掉，**全部转小写**后再匹配：
  - 含 `*` 的行按 `fnmatch.fnmatch(相对路径, 模式)` 匹配，如 `*.min.js`、`docs/generated/*`；
  - 其余行按**路径前缀**匹配：`相对路径 == 该项` 或以 `该项 + "/"` 开头。
  - 命中的目录整棵剪掉、命中的文件不进 `files`；`.ignore` 自身无后缀故天然不进索引，不做特判。
  - **不支持否定规则（`!`）与父目录继承**：只认仓库根这一份，保持「同一仓库两次运行结果一致」。
- `.ignore` 只影响 `files` 集合；`truncated` 判定、排序键与 `rel` / `read` / `text` / `by_suffix` / `line_of` 语义不变。

## feature 相关性兜底（C-MATCHER@5）

- **词表为空不得跳过相关性过滤**：`judge` 的 feature 分支取 `terms = feature_terms(claim.text) or claim_terms(claim.text)`；`feature_terms` 非空时不得混入 `claim_terms`（`or` 短路保证），即已有正确判定逐字不变。
- **两条 `no_evidence` 分支**：两者皆空 → `reason` 为 `需求文本无可用于匹配的关键词`；兜底后过滤仍无证据 → `reason` 为 `未找到与该功能关键词相关的实现`。两条均 `confidence=low`、`locator=None`、`evidence_ids=[]`。
- 非 `ClaimType.feature` 的分支（negation / ability / testing / 默认 supported）不变；分支内不得留两处等价判断。

## 关键词按 ASCII 词边界匹配（C-MATCHER@6 / C-PROBER@8）

- **纯 ASCII 关键词用词边界**：`matcher.mentions(evidence, terms)` 对 `term.isascii()` 为真的项用 `(?<![a-z0-9])term(?![a-z0-9])` 匹配 `f"{file} {snippet}".lower()`；非 ASCII（中文）项仍用子串。中文无词边界概念，且既有判定依赖子串语义，不得改成按字切分。
- **下划线视为分词符**：`_export_rows` 里的 `export` 算命中（前后是 `_`），而 `getLevelNamesMapping` 里的 `eln`（小写后在 `levelnames` 内部）不算。这条区分决定了 `fx-feature` / `fx-contradicted` 的「相关实现」行是否变化——实测把 `_` 纳入边界会误伤 `_export_*`，故边界字符类为 `[a-z0-9]`。
- **为什么必须加边界**：需求文本里的 `.eln` / `.tu` 这类扩展名会被 `claim_terms` 的 `[a-z0-9_]+` 切成 `eln`/`tu`，裸子串会命中 `levelnames`（`logging/__init__.py`）、`_writeLnDecorator`（`unittest/runner.py`）这类无关标识符——压测中「一个模块固定两份文件：.tu 写承诺…，.eln 写实现…」因此把 11 个无关 Python 文件判成「有证据」，且定位首选是 VS Code 插件内嵌的 Python 标准库副本。
- **边界不吞掉真实命中**：`foo.eln` 的 `eln`、独立词 `target`、`@app.get("/export")` 的 `export`、`openpyxl` 仍命中（`.`/`"`/空格不是 `[a-z0-9]`）。`500` 这类数字词同样按边界，`app500` 不再算命中。
- **收窄与判定必须同口径**：`prober.run` 的 feature 分支改为 `[item for item in items if mentions(item, terms)]`，不得再写一遍裸子串判断；`judge` 的反证相关性与 feature 兜底同样只用 `mentions`。
- 词边界只影响「是否命中」，不改变 `terms` 的产生规则（`claim_terms` / `feature_terms` 逐字不变），也不改变 `scanned` 计数。

## 入口兜底（C-PIPELINE@5）

- **不把最大文件当入口**：`_structure_entry` 已删除（原实现取 `structure` 抽取器首条证据，即「行数最多的文件」当入口）。
- **`_facts` 一句话的 `head` 三分支固定**：

| 条件 | 输出 |
| --- | --- |
| 有入口且有路由 | `{entry} 暴露 {n} 个路由` |
| 有入口无路由 | `{entry} 未见路由定义` |
| 无入口 | `未识别到启动入口` |

- 一句话的其余部分（`；{dependency}；{n} 个测试文件。`）与拼接顺序不变；spec 模式多行段的 `入口：` 行按 C-PIPELINE@6 改由路由命中驱动（本契约只约束 `_facts` 的一句话）。

## 入口行与一句话同口径（C-PIPELINE@6）

- **spec 模式「入口：」只由路由命中驱动**：`_overview` 的入口行取 `_route_hits(index)` 的 `evidence.file` 去重后前 3 个；`_route_hits` 与 `_routes_and_entry` 共用同一筛选条件（`EXTRACTORS["entry"]` 中 `strength is not Strength.low` 且 `_route_of(snippet)` 非空），因此同一份报告里 `入口：` 与 `一句话：` 对「有没有入口」的判断必然一致。
- **禁止用全量 entry 证据构造入口行**：`Strength.low` 的 `__main__` / `app.run(` 线索与不含路由定义的文件不得进入入口行——否则会出现 `入口：a.py, b.py` 而 `一句话：未识别到启动入口` 的自相矛盾。
- 无路由命中时输出 `入口：未识别到启动入口`。`文件` / `依赖` / `测试` 三行与返回顺序不变；仅 spec 模式的 `_overview` 受影响，`analyze` 模式的「项目实际是什么」仍由 `_facts` 产出。

## 判定域短路与「不判定」渲染（C-PIPELINE@7 / C-RENDERER@8）

- **判定域外不跑探针**：`_judge_one` 首行判 `claim.out_of_scope`，为真则直接返回 `_scope_verdict(claim)`，**不调用 `prober.run`、不进挑战循环、不产生 `search_trace`**。`_scope` 已按 `not is_judgeable(claim.type)` 标好该字段，故 `architecture` / `scale` / `security` 与外部标注意味着同一条路径。
- **`_scope_verdict` 的固定取值**：`status=no_evidence`、`confidence=low`、`locator=None`、`coverage=none`、`evidence_ids=[]`、`search_trace=[]`、`rounds=1`、`reason=OOS_REASON`、`fix="不补：…"`。三态枚举**不新增第四种**，`out_of_scope` 仍是 `Claim` 上的独立布尔位；`coverage=none` 与空 `search_trace` 的组合满足 `Verdict` 构造期不变量。
- **渲染固定文案**：该条输出 `结论：不判定（超出判定域：架构 / 规模 / 安全类需求不在本次判定范围）` + `该补什么：…` + `audit effort：0 类 0 处`，**不输出「查到」「查过没找到」两段**（没有探针就没有可报的扫描范围）。
- **统计口径**：概览的三态计数只统计 `not claim.out_of_scope` 的条目；存在判定域外条目时追加一行 `- 其中 {n} 条超出判定域，不判定`，`n = 0` 时该行不输出（六份 `fx-*.md` 因此逐字不变）。`## 未覆盖` 排除判定域外条目，避免把「不判定」说成「没有找到任何可查痕迹」。
- `metrics.compute` / `review` / `advice` 的既有排除逻辑不变：判定域外条目不计入 `n_judgeable`、覆盖率与 `audit effort`。

## 「查过 N 处」的双口径（C-TRACE@2 / C-RENDERER@9）

- **两个数，各自定义清楚**：`#### 查过 N 处` 的 N 仍是**按需求累加的扫描次数**，等于所有 `audit effort` 的处数之和（既有守卫不变）；新增的「不同位置」是**按探测项去重后的扫描位置数**，用于回答「到底覆盖了多少不同候选」。
- **`distinct_scanned(trace)` 的去重键是 `(probe.probe, probe.target)`，同键取 `max(scanned)`**。`scanned` 只由 `CANDIDATE_FILES` 与索引规模决定，与 claim 无关；同一探测项被多条需求各扫一遍时扫的是同一批候选，故跨 verdict 只计一次。取 `max` 而非首个值，是因为 `prober.run` 用 `max(scanned, len(hits))` 收口，同一键的 `scanned` 可能因命中数不同而不同，取 max 不会低估。
- **渲染只在两个数不等时补一行**：`- 其中不同位置 {distinct} 处（同一探测项被多条需求重复扫描时只计一次）`，紧跟 `#### 查过` 行；`distinct >= total` 时**不输出任何新行**，因此 `fx-concurrency` / `fx-feature` / `fx-testing` / `fx-challenge` / `fx-contradicted` 五份报告零影响。`fx-spec` 因四条需求共享探针（累加 36、去重 18）按本契约重刷。
- 去重口径**不进入** `TraceSummary` 字段，也不改 `to_dict` 与 JSON 形状；`analyze` 与 `spec` 两种模式用同一函数、同一文案。
- `audit effort：{classes} 类 {scanned} 处` 保持按条累加口径不变：它回答的是「这一条需求花了多少力气」，与概览的去重数不是同一个问题，不得互相换算。

## 符号行抽取与多语言覆盖（C-EXTRACTOR@6）

- **新增 `extractors/symbols.py`**：`SUPPORTS = [ClaimType.feature]`，`kind=code`、`strength=low`；每个文件最多产出 **1 条**证据，取文件内**首个**命中行后 `break`。不做 AST 解析、不建调用图，定位粒度是「文件内首个像定义的文本行」，不是函数边界。
- **`SYMBOL_TOKENS` 至少覆盖九组后缀**：`.py`（`def ` / `class `）；`.js` / `.jsx` / `.ts` / `.tsx`（`function ` / `class ` / `export `）；`.java` / `.cs` / `.kt` / `.kts` / `.scala`（`class ` / `interface ` / `enum `）；`.go`（`func ` / `type `）；`.rs`（`fn ` / `struct ` / `impl ` / `trait `）；`.c` / `.h` / `.cc` / `.cpp` / `.cxx` / `.hpp` / `.hh` / `.hxx`（`class ` / `struct ` / `namespace ` / `template `）；`.rb`（`def ` / `class ` / `module `）。`.php` 与 `.swift` 各一组。
- **索引必须同步扩表**：`index.TEXT_SUFFIXES` 与 `extractors.CODE_SUFFIXES` 一并收录上述后缀，否则这些语言的仓库进不了索引，符号规则不会被调用；扩表后既有抽取器仍只按自身后缀筛选，行为不变。
- 每文件至多 1 条保证 `查过 N 处` 不随文件内符号数量膨胀；`ev-symbols-{n:03d}` 编号按 `index.files` 排序稳定。

## feature 探测与判定同口径（C-PROBER@7）

- **「相关实现」改指 `symbols`**：`PLAN[ClaimType.feature]` 中该探测项为 `ProbeSpec("相关实现", "symbols", "按模块划分的实现文件", ())`，`where_contains` 只能为 `()`——`symbols` 的证据本身就是符号行，再加 `("def ", "class ")` 会把非 Python 仓库全部过滤掉。
- **`CANDIDATE_FILES["symbols"]`** 登记上述全部后缀的 glob（`*.py,*.js,*.jsx,*.ts,*.tsx,*.java,*.cs,*.kt,*.kts,*.scala,*.go,*.rs,*.rb,*.php,*.swift,*.c,*.h,*.cc,*.cpp,*.cxx,*.hpp,*.hh,*.hxx`），与 `EXTRACTORS` 的键集合对齐（既有守卫 `set(CANDIDATE_FILES) == set(EXTRACTORS)`）。
- **收窄与判定层同口径**：`prober.run` 的 feature 分支取 `terms = feature_terms(claim.text) or claim_terms(claim.text)`，与 `matcher.judge` 的 C-MATCHER@5 完全相同；`terms` 为空时退化为类级命中，非空时按 `f"{item.file} {item.snippet}".lower()` 过滤。`feature_terms` 非空时不得混入 `claim_terms`。
- **报告重刷的允许范围**：`reports/fx-*.md` 允许因本契约重刷，但每份 diff 只许落在「相关实现」探针行及其算术连带（`#### 查过 N 处`、`audit effort：M 类 N 处`）；其余任何行变化视为回归。

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
- **B 段：为不可判定条目生成可验收判据**：`provider` 非空时，对每条 `decidable is False` 的条目调用一次 `provider.complete(CRITERIA_PROMPT.format(text=item.text))`，取返回值中第一个非空且命中 `_CRITERIA_CHECK_RE`（数字 + 单位阈值，或 `P9x` / `P5x` / `file:` 定位）的行并截断到 `CRITERIA_MAX_CHARS = 200` 字符，命中则覆盖该条 `suggestion`；没有任何行命中、空串或异常保留规则值（`suggestion` 绝不变空）。`_CRITERIA_CHECK_RE` 独立于 `spec._MEASURABLE_RE`，不得复用后者。`decidable is True` 的条目**一律零调用**——验收基准是 fx-spec 的 5 条里恰有 1 条「高性能」不可判定，故恰好 1 次调用。`prompt` 只含需求原文，**不含仓库文件路径、源码、`Locator`、探测项名**。判据随 JSON 一起落盘固化，后续对账只读该文件、不再重算判据，因此同一份清单两次解析逐字节一致；`load_spec_json` 回读时校验 `schema` 与每项类型，**不读 `provider`、不发起任何调用**。
- **失败一律降级**：超时、非 2xx、JSON 非法、结构缺字段、`content` 非字符串，`complete` 一律返回空串，不重试、不抛异常；`as_llm_fn(None)` 返回 `None`，对账主链路不中断。
- **产物边界**：两个子命令的产物路径只由 `--out` 决定，**六份 `reports/fx-*.md` 逐字不变**（`tests/test_fixtures.py` 守卫），既有 `analyze` / `questions` / `spec` / `score` 的参数与输出一字不改。- **进度只走 stderr（progress@1 / specjson@3 / advice@2 / cli@2）**：`progress.py` 对外提供 `LABEL_CRITERIA = "生成判据"` / `LABEL_ADVICE = "生成建议"` / `TEXT_MAX_CHARS = 40` / `ProgressEvent` / `ProgressFn` / `stderr_progress` / `resolve_progress`，只写调用方传入的 stream，**不写 stdout、不写文件、不 import `specjson` / `advice` / `cli`**。`build_spec_document` / `write_spec_json` / `render_advice` 各增尾随可选参数 `progress: ProgressFn | None = None`，每次模型调用**严格成对**发一次 `start`（`seconds` 恒 `0.0`）与一次 `done`（`seconds` 为 `time.perf_counter()` 差值）；`total` 分别为不可判定条目数与 `len(advice_targets(analysis))`，`label` 分别恒为 `LABEL_CRITERIA` / `LABEL_ADVICE`。`provider is None` 或 `progress is None` 时**零事件**，`items` 内容、顺序与产物字节不变。渲染格式固定：`start` 写 `[{index}/{total}] {label}：{text} ...` 且不换行，`done` 写 `\r[{index}/{total}] {label}：{text} ... {seconds:.2f}s\n`，两次都 `flush()`；`text` 超过 `TEXT_MAX_CHARS` 截断并补 `…`。
- **进度开关三态**：`parse-spec` 与 `advise` 提供 `--progress` / `--no-progress`（`argparse.BooleanOptionalAction`，`dest="progress"`，`default=None`）。`resolve_progress(None, stream)` 按 `stream.isatty()` 自动判定——交互终端显示、管道/重定向/CI 静默；`True` 无条件显示、`False` 静默。**stdout 输出不变**：`parse-spec` 仍只有 `spec: {path}`，`advise` 仍只有 `advice: {path}`；退出码、降级提示与产物路径规则与 @1 一致。
## 误报收紧（C-EXTRACTOR@7 / C-INDEX@4）

- **否定词限定在参数校验型异常消息内不算反证**：新增 `_EXCEPTION_GUARD`（`valueerror(` / `typeerror(` / `keyerror(` / `attributeerror(` / `assertionerror(` / `indexerror(` / `oserror(` / `lookuperror(` / `overflowerror(`）。`_is_negation_line` 逐 marker 定位：行内含 guard token 且该 marker 首次出现的下标经 `_inside_string_literal`（`text[:index]` 中 `"` 或 `'` 计数为奇数即处于引号内）判为处于字符串字面量时跳过该 marker，否则命中即返回 `True`；全部 marker 被跳过时仍按原逻辑判 `TODO_MARKERS`。`raise NotImplementedError(...)` 不在 guard 名单内，仍判为否定。`NEGATION_MARKERS` / `CAP` / `SUPPORTS` / `strength=high` / `snippet` 截断规则不变。
- **requirements 续行拼接**：`_requirements_names` 在逐行解析前先 `re.sub(r"\\\r?\n", " ", text)` 把行尾反斜杠续行（LF 与 CRLF）拼成单行，避免 `--hash` 续行被当成独立声明。`_requirement_name` 的注释剥离、URL/路径排除与 `_NAME_SPLIT` 切分不变；不含续行的文件解析结果逐字不变。
- **工具生成物目录排除**：`SKIP_DIRS` 追加 `.oss-scanner`（带点，与真实目录名一致），`build_index` 用 `entry.name.lower()` 全等比较，该目录整棵不进索引。既有 `cmakefiles` / `SKIP_DIR_PREFIXES` / `.ignore` 行为不变，`reports/fx-*.md` 六份零变化。