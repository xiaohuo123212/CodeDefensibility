# gap-engine 契约（C-SCHEMA@1 / C-PRIORITY@1 / C-TRACE@2 / C-INDEX@2/@3/@4 / C-MATCHER@5/@6/@7/@8/@9/@10 / C-PROBER@5/@7/@8 / C-PIPELINE@5/@6/@7 / C-EXTRACTOR@4/@5/@6/@7/@8 / C-RENDERER@7/@8/@9 / C-DEMO@2 / C-LLM@1（specjson@6） / C-SPEC@2/@3）

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
| C-MATCHER@5/@6/@7/@8/@9/@10 | `src/gap_engine/matcher.py` | `judge`（feature 分支的相关性兜底）、`feature_terms` / `claim_terms`、`CONTRADICTED_QUESTION_TEMPLATE`（`contradicted` 判定）；@6：`mentions`（ASCII 词边界匹配）；@7：`IMPL_TERM_GROUPS` / `impl_terms`（反证相关性的中英实现词扩展）；@8：`_mentions_snippet` / `_GENERIC_TERMS`（反证相关性只看声明本身）；@9：`_name_and_snippet`（`mentions` 的路径只取文件名）；@10：`_claim_params` / `_support_candidates` / `_IMPORT_LINE_RE` / `_DEF_LINE_RE` / `_is_test_file`（正证据最低形态与参数覆盖） |
| C-PIPELINE@5/@6/@7 | `src/gap_engine/pipeline.py` | `analyze_repo` / `analyze_spec` 的 `max_rounds` 与挑战循环（`_judge_one`：只有 `no_evidence` 进第 2 轮）；`_facts` 一句话的入口三分支；@6：`_route_hits` / `_route_files` 与 `_overview` 入口行；@7：`_scope_verdict` 判定域短路 |
| C-EXTRACTOR@4 | `src/gap_engine/extractors/artifact.py` | `extract`（`kind="bench"`、`strength="medium"`、`CAP=40`） |
| C-EXTRACTOR@5 | `src/gap_engine/extractors/negation.py` | `NEGATION_MARKERS` / `extract`（显式否定声明） |
| C-EXTRACTOR@6 | `src/gap_engine/extractors/symbols.py` | `SYMBOL_TOKENS` / `extract`（每文件首个符号行，`kind=code`、`strength=low`） |
| C-EXTRACTOR@7 | `src/gap_engine/extractors/negation.py` + `deps.py` | `_EXCEPTION_GUARD` / `_inside_string_literal`（参数校验型异常消息内的否定词不算反证）；`_requirements_names` 先拼接行尾 `\` 续行 |
| C-EXTRACTOR@8 | `src/gap_engine/extractors/negation.py` | `_FALLBACK_WORDS` / `_TEST_GUARD` / `_MESSAGE_ASSIGN_RE` / `_is_identifier_marker`（标识符、回退说明、测试期望、待抛消息内的否定词不算反证） |
| C-RENDERER@7/@8/@9 | `src/gap_engine/renderer.py` | `render` 的 `结论：` 三态文案、`换假设：{rounds} 轮` 行、局限段措辞；@8：`_scope_note` 与「不判定」块；@9：`_dedup_note` 去重口径行 |
| C-DEMO@2 | `demo/source.py`（新增）+ `demo/app.py` | `extract_zip` / `clone_github` + 四个上限常量；三种输入方式与 UI 约束 |
| C-LLM@1 | `src/gap_engine/llm.py` + `advice.py` + `specjson.py` + `progress.py` + `cli.py` | `LlmProvider` / `HttpLlm` / `load_provider` / `as_llm_fn`；`advice_targets` / `render_advice`；`build_spec_document` / `write_spec_json` / `load_spec_json`；`LABEL_CRITERIA` / `LABEL_ADVICE` / `TEXT_MAX_CHARS` / `ProgressEvent` / `ProgressFn` / `stderr_progress` / `resolve_progress`；`gap parse-spec` / `gap advise` 的 `--progress` / `--no-progress`；specjson@4：`_CRITERIA_CHECK_RE` 与 `_criteria_for` 只采纳含量化阈值或 `file:` 定位的模型返回值；specjson@5：`_strip_restatement` / `_RESTATE_GENERIC`——以需求原文开头的候选先剥离复述前缀（比对时剔除空白与中英文标点），只保留澄清残量；specjson@6：`_overlap_ratio` / `_core_topics` / `_RESTATE_OVERLAP` / `_TOPIC_CORE_MIN`——残量须过三道检查：含量化阈值或 `file:` 定位；与需求核心二字词覆盖率 `< 0.5`（否则判为换语序/加主语的复述）；需求核心词 ≥ 3 时覆盖率不得为 0（否则判为离题）。`CRITERIA_PROMPT` 增加「判据必须针对需求提到的对象，不要替换成需求没提到的指标」约束 |

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

## 反证相关性的中英实现词扩展（C-MATCHER@7）

- **为什么需要**：`judge` 的反证路径是 `claim_terms(claim.text)` 切词后与 `NEGATION_MARKERS` 命中的证据做 `mentions` 相关性判定。中文需求切出的是中文二字词（如「用同步」「语句加锁」），而代码里的否定声明是英文（`Sync context manager entry is not supported...`），两边零重叠，真反证被相关性过滤掉。实测 10 条真反证中 7 条因此判成 `no_evidence`。
- **新词表与函数**：`IMPL_TERM_GROUPS` 与 `FEATURE_TERM_GROUPS` 同构（每组第一个是中文词，其余是英文实现词），`impl_terms(text)` 小写化文本后「命中组内任一词即把整组去重并入」，口径与 `feature_terms` 一致。初始覆盖异步/协程、同步上下文、订阅者、分隔符、压缩、序列化、单例、重入、回调、弱引用、截断、过期、文件描述符、心跳、死锁、写者、平台、进程间等实现词汇。
- **英文触发词走词边界**：`impl_terms` 的触发判定对 ASCII 词复用 C-MATCHER@6 的 `_latin_pattern`（`_group_word_hit`），因此 `AsyncFileLock` 里的 `sync` 是连写标识符的一部分，不触发 `("同步 with", "sync", "synchronous")`。裸子串会把它当触发词，使「AsyncFileLock 支持 async/await」这类真实现被 `asyncio.py:317` 误判为反证——20 条真实现样本的反证数会从 1 抬到 3。
- **「同步」组收窄为 `同步 with`**：只用 `同步` 作中文触发词会让「提供进程间同步」把 `sync` 并入，同样命中 `asyncio.py:317`，误报增加。`同步 with` 对应该行真证据的 `Sync context manager` 语义，故中文触发词收窄为词组。
- **故意不收 `("锁", "lock", "flock")`**：`lock` 在 filelock 代码里遍地都是，纳入会把 20 条真实现样本的误报抬回去。
- **只作用于 `judge` 的反证判定**：`negation_terms` 由 `terms` 与 `impl_terms(claim.text)` 去重合并（C-MATCHER@8 起再剔除 `_GENERIC_TERMS`），仅用于 `negations` 的相关性过滤。`impl_terms` 不得进 `feature_terms`、不得进 `prober`、不得进 feature 分支的 `terms`。
- **不变项**：`claim_terms` / `feature_terms` / `prober.py` / `pipeline.py` / `renderer.py` 输出逐字不变，`NEGATION_MARKERS` 不动；六份 `reports/fx-*.md` 必须逐字不变（`git status --short reports/` 为空）。

## 反证相关性只看声明本身（C-MATCHER@8）

- **为什么需要**：`mentions` 的 haystack 是 `f"{evidence.file} {evidence.snippet}"`，**文件路径参与匹配**。需求里出现包名（如 `FileLock`）时，`src/filelock/` 下**每个**否定行都会因路径命中被判为相关声明。实测「FileLock 支持用 lifetime 参数按文件年龄强制过期」的定位因此落到 `_strict.py:830`——一行讲 Termux 无 `os.link` 的注释，与需求毫无关系。
- **另一处泛词**：`claim_terms("... preserve_lock_file=True ...")` 会切出 `true`，而 `true` 在代码里遍地都是，使 `tests/test_util.py:613`（`pytest.param(True, id="unsupported")` 的参数标识）被当成相关否定声明。
- **新函数 `_mentions_snippet(evidence, terms)`**：与 `mentions` 同构（ASCII 走 `_latin_pattern` 词边界、中文子串），但 haystack **只用 `evidence.snippet`**，不含 `evidence.file`。理由：文件路径只能定位、不能表达语义。
- **泛词表 `_GENERIC_TERMS = frozenset({"true", "false", "none", "null"})`**：反证相关性判定前从 `negation_terms` 中剔除，无区分度的字面量不该决定相关性。
- **只作用于反证路径**：`judge` 内改为
  `negation_terms = tuple(t for t in terms + tuple(x for x in impl_terms(claim.text) if x not in terms) if t not in _GENERIC_TERMS)`，
  `negations = [e for e in relevant if _is_negation(e) and _mentions_snippet(e, negation_terms)]`。
- **不变项**：@9 起 `mentions()` 的路径部分改为只取文件名；`claim_terms` / `feature_terms` / `impl_terms` / `NEGATION_MARKERS` / `prober.py` 不动；六份 `reports/fx-*.md` 必须逐字不变。
- **实测取舍**（用户裁决「先修定位缺陷」）：20 条真实现 `10/9/1` → **`11/9/0`**（误报清零，且一条从被误推翻回到有证据）；10 条真反证 `3/10` → **`1/10`**，但定位准确率 `1/3` → **`1/1`**。`_strict.py:830` 与 `tests/test_util.py:613` 两处误定位消失。

## 路径匹配只认文件名（C-MATCHER@9）

- **为什么需要**：@8 只在反证路径上排除了文件路径，feature 分支仍用「完整路径 + snippet」。需求里出现库名（`FileLock`）时，`src/filelock/` 下每个文件都因目录名命中而成为「相关实现」——「lifetime 强制过期」判 `supported` 并定位到只沾了包名的行。
- **新函数 `_name_and_snippet(evidence)`**：把 `evidence.file` 的 `\` 归一化为 `/` 后取**最后一段**（文件名），与 `snippet` 拼接并小写。`mentions` 改用它；`prober` 的 feature 收窄复用 `mentions`（C-PROBER@8），因此同口径受益。
- **边界**：目录名不再参与匹配，所以 `src/pkg/cli.py` 仍能命中 `cli`（文件名表达功能），但 `src/filelock/_api.py` 不会命中 `filelock`（目录名只表示归属）。
- **不变项**：`feature_terms` / `claim_terms` / `impl_terms` / `NEGATION_MARKERS` / 反证路径的 `_mentions_snippet` 均不动；六份 `reports/fx-*.md` 必须逐字不变。
- **实测**：六份 `reports/fx-*.md` 逐字不变（`git status --short gap-engine/reports/` 为空）。30 条真反证 `supported / no_evidence / contradicted` = **6 / 23 / 1**（6+23+1=30，无判定域外、无不可验收），`supported` 由 18 降到 **6**。32 条真实现 = **supported 8 / 查过没找到 19 / 判定域外 4 / 不可验收 1**（8+19+4+1=32，`contradicted` 0），`supported` 由 12 降到 **8**；precision `N=8/8`（分母 = 确定判断 supported 8 + contradicted 0），recall `N=8/32`，按可判 27 条口径 `N=8/27`。4 条降级原因：`支持可取消的 acquire` 与 `AsyncFileLock 支持自定义 executor 与事件循环` 的正证据全在 `tests/`（`tests/test_async_filelock_acquire_cancellation.py:28`、`tests/test_async_filelock_runner_shutdown.py:23`、`tests/test_async_filelock_transition_admission.py:31`），测试里的同名调用不证明实现支持该参数组合；`SoftFileLease 提供带心跳的过期声明` 与 `SoftFileLease 支持 on_compromise 回调` 的唯一证据是 `src/filelock/_lease.py:62 class SoftFileLease(MarkerSoftFileLock):`，类声明行只证明类存在与基类，不证明参数级功能。

## 正证据的最低形态与参数覆盖（C-MATCHER@10）

- **为什么需要**：30 条真反证样本（`对账引擎/评测-引擎质量/anchor-neg-30.md`）里 18 条被判 `supported`，定位**全部**是 `import` 行（`signer.py:15`）、`tests/*`（`tests/test_leak.py:11`、`tests/async_filelock_cancellation_helpers.py:15`）或纯 `def` 签名（`_api.py:801 def run_in_executor`）。这些行只能证明「名字存在」，不能证明声称的参数组合被支持。例：声称「AsyncFileLock 在 `thread_local=True` 时仍支持 `run_in_executor=True`」，`_api.py:801` 只提到了 `run_in_executor`。
- **新函数 `_claim_params(text) -> tuple[tuple[str, ...], ...]`**：返回**参数组集**，每个元素是一组同义词。成组规则逐条如下：
  - 显式 `k=v`：按 `(?i)\b([a-z_][a-z0-9_]{2,})\s*=\s*(?:true|false|\d+)` 提取参数名并小写化，**每个参数名各自成为一个单元素组** `(name,)`；`_GENERIC_TERMS`（`true`/`false`/`none`/`null`）不进组，同名只保留一组。
  - 概念同义词：`impl_terms` 命中的每个 `IMPL_TERM_GROUPS` 组，**整组按原样**（该组全部词，含中文词，小写化）成为一个组，因此 `过期`/`expire`/`expiry`/`lifetime`/`max_age` 只需出现一个。`impl_terms` 的每个词都归属于它所在的组，**不存在「不属于任何显式参数而被丢弃」的词**，也不存在把某个 impl 词塞进显式参数组的情况；两类组之间互不合并。
  - 组集为空（既无显式 `k=v`、`impl_terms` 也为空）时不启用参数覆盖要求，行为与 @9 完全一致。
- **参数覆盖要求（组间 AND、组内 OR）**：`_claim_params` 非空时，判定式固定为 `all(_mentions_snippet(item, group) for group in _claim_params(claim.text))`——每个组必须被命中（组内任一词出现即算该组命中），所有组都命中才算有效正证据；`_mentions_snippet` 对 ASCII 词走 `_latin_pattern` 词边界（复用 C-MATCHER@6）、对中文走子串匹配。
- **弱支持形态**（不计入 `supported` 候选，但仍留在 `relevant` 供报告展示）：
  - `_IMPORT_LINE_RE = re.compile(r"^\s*(from\s+\S+\s+)?import\s")` 命中者；
  - `_is_test_file(evidence)`：路径（`\` 归一化为 `/`）含 `/tests/`、`/test_/` 或文件名以 `test_` 开头；仅当 `claim.type is not ClaimType.testing` 时排除；
  - `_DEF_LINE_RE = re.compile(r"^\s*(async\s+)?def\s+\w+\s*\(")` 命中且该行未同时提及全部 `_claim_params` 者。
- **新函数 `_support_candidates(claim, relevant)`**：返回通过上述全部过滤的正证据（`not _is_negation(e)`）。
- **`supported` 分支改用 `_support_candidates`**：过滤后为空 → 返回 `no_evidence`，`confidence=Confidence.low`，`reason="仅见名称或签名，未见声称参数组合的实现"`，`locator=_locator_evidence(relevant)`，`coverage=_coverage(trace)`，`rounds` 透传。
- **`_locator_evidence` 对非反证结论的定位**：在「非依赖声明、非否定行」之上，再优先排除 `_is_test_file` 与 `_IMPORT_LINE_RE` 命中的证据；不得让 `supported` 的定位指到 `tests/`。
- **既有用例预期随 @10 收紧**：`test_matcher.py::test_impl_terms_do_not_admit_unrelated_negation` 的断言由 `supported` 改为 `no_evidence`（保留 `not contradicted`）。理由：`AsyncFileLock` 是异步锁，`asyncio.py:330` 的 `with` 在 async 上下文，对「同步 with」属于语义错配，该行不应再算有效正证据；用例原本要守的「不相关 Windows 否定声明不构成反证」不变。
- **不变项**：反证分支（`contradicted` 优先于一切）不动；`_ABILITY_TYPES` 的 bench 分支不动；`no_evidence` 的既有首次返回不动；`claim_terms` / `feature_terms` / `impl_terms` / `_mentions_snippet` / `NEGATION_MARKERS` / `prober.py` / `negation.py` 一律不动。
- **验收口径**：30 条真反证 `supported` 由 18 降到 ≤ 8（实测 6）；32 条真实现 `supported` 由 12 不得低于 8（实测 8）；real 侧 4 条降级逐条注明：2 条证据全在 `tests/`、2 条证据仅类声明行；六份 `reports/fx-*.md` 的 diff 只允许落在受影响的判定行，必须逐份核对并在交付说明里逐条列出。
- **实测**：六份 `reports/fx-*.md` 逐字不变（`git status --short gap-engine/reports/` 为空）。30 条真反证 `supported / no_evidence / contradicted` = **6 / 23 / 1**（6+23+1=30，无判定域外、无不可验收），`supported` 由 18 降到 **6**。32 条真实现 = **supported 8 / 查过没找到 19 / 判定域外 4 / 不可验收 1**（8+19+4+1=32，`contradicted` 0），`supported` 由 12 降到 **8**；precision `N=8/8`（分母 = 确定判断 supported 8 + contradicted 0），recall `N=8/32`，按可判 27 条口径 `N=8/27`。4 条降级原因：`支持可取消的 acquire` 与 `AsyncFileLock 支持自定义 executor 与事件循环` 的正证据全在 `tests/`（`tests/test_async_filelock_acquire_cancellation.py:28`、`tests/test_async_filelock_runner_shutdown.py:23`、`tests/test_async_filelock_transition_admission.py:31`），测试里的同名调用不证明实现支持该参数组合；`SoftFileLease 提供带心跳的过期声明` 与 `SoftFileLease 支持 on_compromise 回调` 的唯一证据是 `src/filelock/_lease.py:62 class SoftFileLease(MarkerSoftFileLock):`，类声明行只证明类存在与基类，不证明参数级功能。

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

## 否定作用域（C-EXTRACTOR@8）

真实仓库的否定词大量出现在"不是功能缺失"的语境里，@7 仅覆盖了同一行内 `raise ValueError(...)` 一种。@8 按六种形态补齐作用域判定，全部规则只收紧、不放宽。

- **标识符内的否定词不算反证**：`_is_identifier_marker(lowered, index, marker)` 在 marker 为 ASCII 时判定——marker 前一个字符或后一个字符属于 `[A-Za-z0-9_]`，或 marker 之后跳过空白紧跟 `=` 时，视为标识符或变量名用法，跳过该 marker。覆盖 `_lifetime_unsupported_reason`、`_HARD_LINK_UNSUPPORTED_ERRNOS`、`unsupported = (` 等形态。中文 marker（`不支持` 等）不参与该判定。
- **回退/降级说明不算反证**：行内（小写化后）命中 `_FALLBACK_WORDS`（`falling back` / `fallback` / `回退` / `降级` / `退化`）时整行跳过 marker 检查。典型为「flock 在此文件系统不可用，回退到 SoftFileLock」——这句描述的是降级路径，恰恰是「自动回退」需求的实现证据，不得当作反证。
- **测试断言内的期望消息不算反证**：行内命中 `_TEST_GUARD`（`pytest.raises` / `assertraises` / `assertwarns` / `assert_raises`）且该 marker 首次出现经 `_inside_string_literal` 判为处于字符串字面量时跳过。测试里 `match="... is not supported ..."` 是对异常文本的期望，不是代码声明。
- **待抛消息的字符串赋值不算反证**：`_MESSAGE_ASSIGN_RE` 匹配 `^(msg|message|reason|detail|err_msg|errmsg)\s*=\s*[frbu]?['"]` 时视同 `_EXCEPTION_GUARD`，只在该 marker 处于字符串字面量内时跳过（沿用 @7 的 `_inside_string_literal` 语义）。覆盖 `msg = f"preserve_lock_file=True is not supported by ..."` 与 `msg = "run_in_executor is not supported when thread_local is True"` 这类参数组合约束。
- **辅助判定 `_in_comment(lowered, index)`**：行（`lstrip()` 后）以 `_COMMENT_PREFIXES`（`#` / `//` / `/*` / `*`）开头，或行内首个 `#` 的下标小于 marker 下标时，判定该 marker 落在注释区（覆盖行尾注释）。
- **代码表达式的布尔取反不算反证**：`_is_control_flow_expression(lowered, index)` 在三个条件**同时**成立时跳过该 marker——marker 不处于字符串字面量内、`_in_comment` 为假（即落在代码区）、整行不含 CJK 字符（`\u4e00`–`\u9fff`）；再要求行内命中 `_CONTROL_FLOW`（`if ` / `elif ` / `while ` / ` and ` / ` or ` / `return ` / `assert `）之一。覆盖 `if preserve and not supported:` 与 `return not supported`。注释里的自然语言否定（`# if 需要就 return，暂不支持并发`）与行尾注释里的英文否定（`x = 1  # ... not implemented`）均不满足注释区/ASCII 条件，仍判为反证；`if 不支持:` 因含 CJK 亦仍判为反证。
- **注释里引号包裹的纯英文短语不算反证**：`_is_english_quoted_in_comment(lowered, index)` 要求 marker 满足 `_in_comment`、该 marker 处于字符串字面量内、且整行不含 CJK 字符。典型为 `# cannot name "operation not supported" as the errno here`（讲 errno 语义）。中文注释里的「暂不支持」不在引号内，仍判为反证。
- **不变项**：`NEGATION_MARKERS` / `TODO_MARKERS` / `TODO_CONTEXT` / `_EXCEPTION_GUARD` / `CAP=40` / `SUPPORTS` / `strength=high` / `snippet` 截断 / 每行去重 / fixture 中否定为空的断言全部不变；中文注释里的「暂不支持」仍判为反证。