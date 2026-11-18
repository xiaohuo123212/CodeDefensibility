# 压测记录：elench-cpp（2026-11-18）

本文是**压测留痕**，不是产品报告。结论只描述本次实测，不代表对所有仓库的普遍结论；压测当场（2026-11-18）**未修改任何代码**，发现项仅作记录。修复后的状态与复测数据见 §6。

## 1. 对象与方法

- 被测仓库：`C:/Users/haoll/Documents/deepseek-harness/default-workspace/elench-cpp`（作者自有项目，非第三方）
- 目录体积 301 MB，含 `build/` 下大量权限受限临时目录
- 索引实际收录 **1440** 个文本文件、**137273** 行、**40** 个测试文件（压测时值；修复后复测值见 §6）
- 排除项：`build/`、`.git/` 等（`index.py` 的 `SKIP_DIRS`）；非白名单后缀；≥400 KB 的单文件
- 索引上限 `max_files=4000` **未触发**（1440 < 4000），压测时索引对象尚无截断标记，故不存在可读取的截断状态

复现命令（在 `gap-engine/` 下执行）：

```bash
python -m gap_engine.cli analyze "<repo>" --out out/report.md --json out/analysis.json
python -m gap_engine.cli spec    "<repo>" --spec req.md --out out/spec-report.md
python -m gap_engine.cli questions "<repo>" --spec req.md --top 10
```

本次使用的 5 条需求清单（`req.md`）：

```markdown
- 零第三方依赖
- 提供 C++ 代码生成后端
- 支持 VS Code 编辑器插件
- 支持成本与复杂度静态分析
- 提供基准测试
```

## 2. 性能与稳定性

压测时（修复前）实测：

| 命令 | 耗时 | 检索规模 | 退出码 |
|---|---|---|---|
| `analyze` | 12.95 s | 查过 19325 处（5 条声称，10 类探测项） | 0 |
| `spec` | 13.56 s | 查过 19195 处（5 条需求，14 类探测项） | 0 |
| `questions` | 13.61 s | — | 0 |

三次执行全部正常退出，无异常、无崩溃；`build/` 下的权限拒绝未导致中断（遍历时 `OSError` 被跳过）。耗时量级可接受，**未发现性能或稳定性问题**。修复后复测的耗时与检索规模见 §6。

三态分布：`analyze` 有证据 4 / 没找到 1 / 有反证 0；`spec` 有证据 3 / 没找到 2 / 有反证 0。

## 3. 已复核为准确的部分

- **「依赖 0 个」是准确的**：该项目 `pyproject.toml` 写 `dependencies = []`，`package.json` 亦无 `dependencies`。这是项目自身的零依赖承诺，不是引擎漏读。
- 「40 个测试文件」「文件 1440 个 / 代码 137273 行」与独立统计一致。

## 4. 发现项

### P0-1 中文需求关键词为空时跳过相关性过滤，直接判 supported — **已修**

实证（同一份清单，压测时）：

| 需求 | `classify` 类型 | `feature_terms` | 判定 |
|---|---|---|---|
| 零第三方依赖 | `feature` | `()` | **supported** |
| 提供 C++ 代码生成后端 | `feature` | `()` | **supported** |
| 支持成本与复杂度静态分析 | `feature` | `()` | **supported** |
| 提供基准测试 | `testing` | `()` | no_evidence（正确） |

机制：`matcher.py` 的 `feature_terms` 只认 `FEATURE_TERM_GROUPS` 固定词表，中文需求普遍命中不到；`matcher.py` 的过滤写成 `if terms:`，**词表为空即整段跳过**，于是任何满足 `claim.type in evidence.supports` 的证据都被算作支持证据，最终走到 `supported`。

「零第三方依赖」的报告里同时出现「依赖声明：0 处（扫过 3 处）」与 `supported`，判据与证据自相矛盾。

此条**不限于 C++ 仓库**：任何不含该词表词条的中文需求都可能被同样误判，属系统性误报源，直接影响误报率指标。

修复与复测：见 §6（`C-MATCHER@5`：词表为空时兜底 `claim_terms`，兜底后仍无相关证据或连关键词都提不出来一律 `no_evidence`）。

### P0-2 C++ 源文件不在索引白名单，却被判「有证据」 — **部分修：仅纳入索引，不承诺语义抽取**

- `index.py` 的 `TEXT_SUFFIXES` 只有 Python 生态后缀，压测时**无 `.cpp / .h / .hpp / .c / .cc`**
- 该仓库有 839 个 `.cpp`、215 个 `.h`、107 个 `.hpp`、189 个 `.c`、48 个 `.cc`、1138 个 `.eln`，**全部不进索引**
- 因此「提供 C++ 代码生成后端」的 `supported` 与任何 C++ 代码无关，是 Python 脚本里的路由命中凑出来的

修复与复测：见 §6（`C-INDEX@2`：`.c/.h/.cc/.cpp/.cxx/.hpp/.hh/.hxx` 纳入索引；本轮不给 C/C++ 写新的抽取器规则）。

### P1-3 归档目录未排除，归档脚本成为入口与证据 — **已修**

报告把 `_archive/2026-11-18-scripts/migrate_docs.py`、`_archive/2026-11-18-scripts/rename_ch.py` 列为入口并给出定位。`index.py` 的 `SKIP_DIRS` 不含 `_archive` 一类归档目录。

修复与复测：见 §6（`C-INDEX@2`：`_archive` / `_archived` / `archive` / `_old` / `old` / `deprecated` 按目录名精确排除）。

### P1-4 入口兜底把「最大文件」当作入口文件 — **已修**

`pipeline.py` 的 `_structure_entry` 取 `structure` 抽取器的首条证据路径，而该路径是「行数最多的文件」；`pipeline.py` 在未识别到路由时用它兜底。结果报告首段输出：

```
一句话：AI语言设计入门.md 未见路由定义；依赖 0 个；40 个测试文件。
```

把一篇中文文档当作入口文件，措辞与事实不符。

修复与复测：见 §6（`C-PIPELINE@5`：删除 `_structure_entry`，无入口时一句话输出 `未识别到启动入口`）。

### P1-5 对非 Python 仓库的「相关实现」恒为 0 — **已修（第二轮：符号层）**

由 P0-2 直接导致：报告显示「相关实现：0 处（扫过 1440 处）」，但该仓库的实现主体是 C++ 与 `.eln`。引擎当前的覆盖面是 Python 生态仓库，对 C++ 仓库不具备「相关实现」层级的分析能力。

修复与复测：见 §6（C/C++ 文件已进索引）；第二轮按 `C-EXTRACTOR@6` / `C-PROBER@7` 补了符号抽取层，`相关实现` 的扫过处数由 1460 变为 968（全部由 `symbols` 产出，见 §7）。

## 5. 结论与后续

- 性能与稳定性达标，可作为大仓库压测的正面证据（1440 文件 / 13.7 万行 / 约 13 秒 / 三次零失败）。
- 质量侧存在 2 个 P0、3 个 P1，其中 **P0-1 是系统性误报源**，优先级最高。
- 本次按决定**只留痕、不改代码**。建议顺序：P0-1（`matcher` 相关性过滤，须变更契约并重刷六份报告）→ P1-3（归档目录排除）→ P1-4（入口兜底措辞）→ P0-2/P1-5（扩索引白名单至 C++，属产品范围扩张）。
- 上述 P0-1 / P1-3 / P1-4 已按契约流程修复，P1-5 在第二轮补符号层后修复，P0-2 按「仅纳入索引」范围部分修复，复测数据见 §6 与 §7。

## 6. 修复与复测（2026-11-18）

修复按契约 `C-INDEX@2` / `C-MATCHER@5` / `C-PIPELINE@5` 落地，随后在同一台机器、同一仓库、同一份 5 条需求清单上重跑。下表数字均为本轮实测值；未实测的项目不填数字（禁止估算）。

复测命令（在 `gap-engine/` 下执行）：

```bash
python -m gap_engine.cli analyze "<repo>" --out out/stress-report.md --json out/stress-analysis.json
python -m gap_engine.cli spec    "<repo>" --spec out/req.md --out out/stress-spec-report.md
python -m gap_engine.cli questions "<repo>" --spec out/req.md --top 10
```

修复前后对照（同一仓库、同一份需求清单）：

| 项目 | 压测时（修复前） | 复测（修复后） |
|---|---|---|
| 索引文件数 / 代码行 | 1440 / 137273 | 1460 / 140010 |
| 索引内 C/C++ 头源文件 | 0 | 31 |
| 索引内归档目录文件（`_archive` / `_archived` / `archive` / `_old` / `old` / `deprecated`） | `_archive/2026-11-18-scripts/*.py` 命中 | 0 |
| `RepoIndex.truncated`（`max_files=4000`） | 无该字段 | `False` |
| `analyze` 三态（有证据 / 没找到 / 有反证） | 4 / 1 / 0 | 1 / 4 / 0 |
| `spec` 三态（有证据 / 没找到 / 有反证） | 3 / 2 / 0 | 0 / 5 / 0 |
| 报告首段一句话 | `AI语言设计入门.md 未见路由定义；依赖 0 个；40 个测试文件。` | `未识别到启动入口；依赖 0 个；40 个测试文件。` |
| `相关实现` | 0 处（扫过 1440 处） | 0 处（扫过 1460 处） |

耗时与退出码（修复后同一轮实测）：

| 命令 | 耗时 | 检索规模 | 退出码 |
|---|---|---|---|
| `analyze` | 14.01 s | 查过 19790 处（5 条声称，5 类探测项） | 0 |
| `spec` | 15.00 s | 查过 19260 处（5 条需求，14 类探测项） | 0 |
| `questions` | 14.67 s | — | 0 |

`truncated` 语义抽查（同一仓库，另传 `max_files`）：`max_files=100` → 收录 100 个、`truncated=True`；`max_files=1460`（恰好等于全文数）→ 收录 1460 个、`truncated=False`。

五项发现的修复状态：

| 发现 | 状态 | 复测证据 |
|---|---|---|
| P0-1 中文需求关键词为空时跳过相关性过滤 | **已修** | 5 条需求全部由 `supported` 收敛为 `no_evidence`（`spec` 三态 3/2/0 → 0/5/0）；`零第三方依赖` 不再在有「依赖声明：0 处」的报告里被判 supported |
| P0-2 C++ 源文件不在索引白名单 | **部分修：仅纳入索引，不承诺语义抽取** | 排除 `build/` 等既有排除目录且 <400 KB 的 C/C++ 文件 31 个，索引内 31 个（压测时 0 个）；`相关实现` 仍为 0 处（扫过 1460 处）——本轮不新增 C/C++ 抽取器，`Evidence` 仍取决于既有抽取器是否命中 |
| P1-3 归档目录未排除 | **已修** | 索引内归档目录命中 0 个；报告不再出现 `_archive/2026-11-18-scripts/*.py`。名称含 `archive` 的正常文件（如 `editors/vscode/python/archive_specs.py`）按目录名精确匹配规则不受影响 |
| P1-4 入口兜底把「最大文件」当入口 | **已修** | 报告首段一句话改为 `未识别到启动入口；依赖 0 个；40 个测试文件。`；`_structure_entry` 已删除 |
| P1-5 非 Python 仓库「相关实现」恒为 0 | **部分修** | C/C++ 文件已进索引（31 个），但 `相关实现` 仍为 0 处；语义抽取按 P0-2 所述不在本轮范围 |

残留观察（不在本轮范围，留作后续）：

- `spec` 模式多行段仍输出 `入口：cpp/docnums/parity.py, editors/vscode/build-vsix.py, editors/vscode/python/archive_specs.py`，与一句话的 `未识别到启动入口` 并存。按 `C-PIPELINE@5`，`_project_facts` 的多行段本轮不改，入口列表仍取 `structure` 证据。
- `analyze` 的探测项类别由 10 类降为 5 类（关键词集合改变后部分探测项不再触发）。
## 7. 第二轮修复与复测（2026-11-18，同日）

第二轮只做两件事：修「`入口：` 与一句话自相矛盾」，并按 `C-EXTRACTOR@6` / `C-PROBER@7` 给主流语言补符号抽取，让「相关实现」在非 Python 仓库不再恒为 0。

| 观察项 | 第一轮修复后 | 第二轮修复后（本轮实测） |
|---|---|---|
| `spec` 报告 `入口：` 行 | `cpp/docnums/parity.py, editors/vscode/build-vsix.py, editors/vscode/python/archive_specs.py`（全量 `entry` 证据） | `未识别到启动入口`（与一句话同口径，`C-PIPELINE@6`） |
| `symbols` 证据条数 | 不存在 | **884 条**（`.py` 861 / `.cpp` 18 / `.js` 5） |
| `相关实现` 扫过处数 | 0 处（扫过 1460 处） | 0 处（扫过 **968** 处，全部由 `symbols` 产出） |
| 索引文件 / 行数 | 1460 / 140010 | 1460 / 140010（本轮未再扩表） |
| `analyze` 耗时 | 13.18 s | 11.19 s |
| `spec` 耗时 | 15.07 s | 12.38 s |

关于 `相关实现` 仍为 0：**扫过 968 处**已证明符号抽取生效（第一轮该行是「扫过 1460 处」但抽取器只产出元数据行，永远匹配不到）。仍 0 命中是**词表问题，不是抽取器问题**——例如「提供 C++ 代码生成后端」两路关键词只有 `代码生成后端`，而仓库里的符号行是 `class Lexer` / `namespace {` 这类。本轮 R8 的目标（符号层对主流语言生效）已达成，语义匹配留作下一轮。

第二轮新发现（不在本轮范围，见 `next-round-todo.md`）：

- **CMake 生成目录未排除**：`cpp/docnums/build-cmake/CMakeCache.txt` 与 `cpp/docnums/build-cmake/CMakeFiles/4.4.4/CompilerIdCXX/CMakeCXXCompilerId.cpp` 进入索引，并成为「覆盖率产物」「symbols」证据。`SKIP_DIRS` 只有精确名 `build`，不覆盖 `build-cmake`。
- **换假设计划丢失关键词相关性**：「支持 VS Code 编辑器插件」的 4 类探针全部 0 处，而同仓库有 561 个符号行命中 `code`——替代计划把「相关实现」换成了「结构指标」，需求关键词没有传下去。
- **文件名含 `archive` 不受 `SKIP_DIRS` 约束**：符合「只匹配目录名」的契约，但 `editors/vscode/python/archive_specs.py` 这类文件是否该排除需要单独决策。
## 8. 第三轮修复与复测（2026-11-18，同日）

第三轮做四项：CMake 生成目录排除与仓库根 `.ignore`（`C-INDEX@3`）、判定域短路与「不判定」渲染（`C-PIPELINE@7` / `C-RENDERER@8`）、「查过 N 处」的双口径（`C-TRACE@2` / `C-RENDERER@9`）。

| 观察项 | 第二轮修复后 | 第三轮修复后（本轮实测） |
|---|---|---|
| 索引文件数 | 1460 | **1454** |
| `build-cmake` / `CMakeFiles` / `CompilerIdCXX` 命中 | 有（`cpp/docnums/build-cmake/...`） | **0** |
| `spec` 概览 | 查过 19260 处（5 条需求，14 类探测项） | 查过 **13893** 处（5 条需求，10 类探测项），其中不同位置 **5614** 处 |
| `spec` 三态（有证据 / 没找到 / 有反证） | 0 / 5 / 0 | 0 / 4 / 0，另有 **1 条超出判定域，不判定** |
| 「支持 VS Code 编辑器插件」 | 判成 architecture，4 类探针全 0 处，`no_evidence` | `结论：不判定（超出判定域：架构 / 规模 / 安全类需求不在本次判定范围）`、`audit effort：0 类 0 处`、不进三态 |
| `入口：` 行 | `未识别到启动入口` | `未识别到启动入口`（不变） |
| 测试 | 494 passed | **505 passed** |

口径变化说明（三处都**不是判定结果变化**）：

- 「查过」19260 → 13893 有两个原因：索引 -6 个生成文件；「支持 VS Code 编辑器插件」不再跑 4 类探针（该类需求 14 类探测项 → 10 类）。
- 三态 0/5/0 → 0/4/0：那条需求从「架构类 `no_evidence`」改为「不判定」，`out_of_scope` 条目不进三态分母（`C-RENDERER@8`）。
- `13893` 仍是**按需求累加的扫描次数**，等于各条 `audit effort` 之和；`5614` 是按 `(probe, target)` 去重后的**不同位置数**。两个数同时可见，避免把累加数读成不同位置数（`tests/test_fixtures.py` 与 `tests/test_report_math.py` 守卫）。

四项的处置结论见 `next-round-todo.md` 对应条目的「状态」段。`elench-cpp` 仓库根没有 `.ignore`，故 `editors/vscode/python/archive_specs.py` 仍按现状进入索引——本轮提供的是**声明机制**，不是文件名规则。
### 8.1 `analyze` 侧子串误命中（`C-MATCHER@6` / `C-PROBER@8`）

第三轮复测发现 `analyze` 的 2 条「有证据」里，有一条是误报：「一个模块固定两份文件：.tu 写承诺（人审、人签），.eln 写实现（可以整份重写）」的命中全部来自 `eln` 的**裸子串**匹配——`logging/__init__.py:126` 的 `getLevelNamesMapping`、`unittest/runner.py:16` 的 `_writeLnDecorator` 都把 `eln` 嵌在更长的标识符里，且定位首选是 VS Code 插件内嵌的 Python 标准库副本。

修法：`matcher.mentions` 对纯 ASCII 关键词改用词边界（下划线视为分词符，`_export_rows` 的 `export` 仍命中），`prober.run` 的 feature 收窄复用同一函数，保证与判定层同口径。

| 观察项 | 修复前 | 修复后（实测） |
|---|---|---|
| 该条命中数 | 11 处 | **9 处** |
| 命中里含 stdlib 副本 | 有（`editors/vscode/runtime/Lib/...`） | **0**，仅 `tests/cases/*.py` |
| 命中上下文 | `levelnames` / `_writeLnDecorator` 等字母连写 | 仅 `def _run(eln, tu, *args)` 这类独立词 |
| `analyze` 三态 | 2 / 3 / 0 | 2 / 3 / 0（两条 supported 均保留） |
| 六份 `fx-*.md` | — | **零变化**（`_export_*` 仍命中，守卫 46 项全绿） |
| 测试 | 505 passed | **509 passed** |

剩余 9 处是 `tests/cases/test_*.py` 里把 `eln`/`tu` 当模块参数的真实用法，属于该仓库「.tu/.eln 双文件模块」的真实痕迹，不再改判。另一条 supported（「签名的一部分（.tu 里的 target）…」）的定位是 `tools/kappa_vs_measured.py`，与需求里的 κ 核对语义对应，保留。
