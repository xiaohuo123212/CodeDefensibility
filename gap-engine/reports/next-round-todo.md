# 下一轮待改清单（2026-11-18 第二轮复测产出）

> **第三轮处置结论（2026-11-18 晚）**：四项全部结案。item1 / item3 已修，item2 按「修判定域、输出不判定」的裁定实施（不改 `ALTERNATE_PLANS`、不动词表），item4 改为仓库根 `.ignore` 机制而非文件名规则。测试 `494 → 509 passed`，契约升到 `C-TRACE@2` / `C-INDEX@3` / `C-MATCHER@6` / `C-PROBER@8` / `C-PIPELINE@7` / `C-RENDERER@9` / `C-EXTRACTOR@6`。实测数据见 `reports/stress-elench-cpp.md` §8 与 §8.1。

本文件是交接口径：第二轮修复已全部落地并通过 `494 passed`，下面四项是复测中**新暴露**、当时明确不修的问题。每条都给了位置、现象、复现方式与验收口径，可直接照着改。

## 0. 先读这几条硬约束

- 契约唯一权威是 `contract/CONTRACT.md`；**改代码前先把契约改成新版本号**（`@n+1`），再改实现与测试。
- 三态只有 `supported` / `contradicted` / `no_evidence`，**禁止 `partial`**；AI 不进三态；`--llm` 默认关闭。
- **禁止为过测试放宽守卫**：`tests/test_fixtures.py` 的「六份 `reports/fx-*.md` 与 CLI 输出逐字一致」是验收线，不是障碍。
- 零第三方依赖（`pyproject.toml` 的 `dependencies = []`），只用标准库。
- 指标一律写实测值，未实测就留空，**禁止估算 N**。
- 本轮 `reports/fx-*.md` 的 diff 只允许落在「相关实现」探针行及其算术连带（`#### 查过 N 处`、`audit effort：M 类 N 处`）；下一轮改动若触及报告正文，必须先想清楚守卫怎么过。

## 1. CMake 生成目录未排除（建议优先级 P0）

**位置**：`src/gap_engine/index.py` 的 `SKIP_DIRS`。

**现象**：`cpp/docnums/build-cmake/CMakeCache.txt:3`、`cpp/docnums/build-cmake/CMakeFiles/4.4.4/CompilerIdCXX/CMakeCXXCompilerId.cpp:449` 进入索引，并成为「覆盖率产物」与 `symbols` 的证据。`SKIP_DIRS` 里只有精确名 `build`，`build-cmake` 不在其中。

**为什么重要**：生成目录里的路径、编译器探测文件都是噪音，会把「查过 N 处」抬高并污染证据定位；同一类目录名还有 `build-*`、`cmake-build-*`、`.cmake/`、`out/`（CMake/VS 默认输出目录）。

**复现**：

```bash
# 在 gap-engine/ 下
python -c "
import sys; sys.path.insert(0,'src')
from pathlib import Path
from gap_engine.index import build_index
idx = build_index(Path(r'C:/Users/haoll/Documents/deepseek-harness/default-workspace/elench-cpp'))
print(len(idx.files))
print([idx.rel(p) for p in idx.files if 'build-cmake' in idx.rel(p)][:5])
"
```

**验收口径**：上述命令输出的列表为空；`1390 <= len(idx.files) < 1460`（真实源码不应被一起排除）；六份 `fx-*.md` 逐字不变（夹具里没有这类目录，理应零影响）。

**注意**：`SKIP_DIRS` 的匹配语义是「目录名全等」，若要支持 `build-*` 前缀，必须在 `build_index` 里新增前缀判定，**不能**把 `build-` 塞进集合——集合是按全等匹配的。

**状态（第三轮）：已修（`C-INDEX@3`）**。`SKIP_DIRS` 追加 `cmakefiles`，目录判定改 `entry.name.lower() in SKIP_DIRS`（此前大小写敏感，`CMakeFiles/` 同样漏网）；新增 `SKIP_DIR_PREFIXES = ("build-", "cmake-build-")` 按前缀整棵剪掉，**故意不收录** `out`（常是正常包名）与 `.cmake`，二者需排除时由仓库自己的 `.ignore` 声明。实测 elench-cpp：索引 `1460 → 1454`（-6），`build-cmake` / `cmakefiles` / `compileridcxx` 命中 **0**，`1454` 落在验收区间内；六份 `fx-*.md` 零影响（夹具无此类目录）。

## 2. 换假设计划丢失需求关键词相关性（建议优先级 P0）

**位置**：`src/gap_engine/prober.py` 的 `ALTERNATE_PLANS`（约 130-134 行）与 `run()` 的轮次分支（约 200-220 行）。

**现象**：elench-cpp 上「支持 VS Code 编辑器插件」被分到「结构指标 / 依赖 / 配置 / 入口」4 类探针，全部 0 处；同一仓库有 561 个符号行命中关键词 `code`（`editors/vscode/extension.js:26 function cfg()` 等）。第 1 轮 `PLAN[feature]` 有五类（含「相关实现」），换假设后只剩四类且**没有一类带关键词收窄**。

**为什么重要**：这是 P1-5 的另一半。符号层已经能产出命中（第二轮已修），但替代计划把最有信息量的「相关实现」换掉了，导致 C++ 仓库的功能需求即使有实现也报 0 处。

**复现**：

```bash
python -c "
import sys; sys.path.insert(0,'src')
from pathlib import Path
from gap_engine.index import build_index
from gap_engine.extractors import EXTRACTORS
from gap_engine.matcher import feature_terms, claim_terms
idx = build_index(Path(r'C:/Users/haoll/Documents/deepseek-harness/default-workspace/elench-cpp'))
ev = EXTRACTORS['symbols'](idx)
terms = feature_terms('支持 VS Code 编辑器插件') or claim_terms('支持 VS Code 编辑器插件')
print(len(ev), terms, sum(1 for e in ev if any(t in f'{e.file} {e.snippet}'.lower() for t in terms)))
"
```

**验收口径**：`spec` 报告里该需求要么出现非 0 的「相关实现」，要么替代计划明确写出「本计划不含关键词收窄」；并且 `no_evidence` 的 `reason` 不得与已查到的 561 处命中自相矛盾（这正是 P0-1 当初修的病）。

**注意**：改 `ALTERNATE_PLANS` 会改 `reports/fx-challenge.md`（换假设 2 轮那条链）。动手前先跑一遍 `tests/test_fixtures.py`，确认 diff 范围可解释。

**状态（第三轮）：根因与原文不同，已按裁定结案（`C-PIPELINE@7` / `C-RENDERER@8`）**。实测两条叠加：① `claimer.py` 的 `ClaimType.architecture` 词表含「**插件**」，该需求被判成架构类（`out_of_scope=False`）；② `pipeline._judge_one` 从不看 `claim.out_of_scope`，架构类照样跑 `_SHARED_SPECS`（结构指标/依赖/配置/入口，**无任何关键词收窄**）并给出 `no_evidence`。即：一条本应「不判定」的需求被当成可判定需求处理了，而不是「替代计划丢了关键词」。裁定为**修判定域**：`_judge_one` 首行短路 `claim.out_of_scope` → `_scope_verdict`，不跑探针、不进挑战循环、不产 `search_trace`；渲染固定输出 `结论：不判定（超出判定域…）` + `audit effort：0 类 0 处`。**未改** `ALTERNATE_PLANS` 与 `claimer.py` 词表，故 `fx-challenge.md` 的换假设链不变。实测该条 now 输出「不判定」，概览追加 `- 其中 1 条超出判定域，不判定`。原文验收口径（非 0 相关实现 / 明确写不含关键词收窄）不再适用——该条已不在判定域内，`audit effort` 按契约恒为 0。

## 3. 报告「查过 N 处」的口径偏大（建议优先级 P1）

**位置**：`src/gap_engine/renderer.py` 与 `src/gap_engine/trace.py`。

**现象**：`spec` 报告概览写「查过 17784 处」，但逐条明细相加与之一致性依赖 `scanned` 累加；同一 `symbols` 证据会同时被 5 条需求各扫一遍（968 × 5），导致「查过」数远大于实际不同位置数。第一轮压测已记录「`analyze` 探测项类别由 10 类降为 5 类」，同类口径问题。

**验收口径**：概览数仍等于明细 `scanned` 之和（`tests/test_report_math.py` 有守卫），但报告需要能区分「去重后的不同位置数」与「按需求累加的扫描次数」，否则对手会质疑数字注水。

**状态（第三轮）：已修（`C-TRACE@2` / `C-RENDERER@9`）**。新增 `trace.distinct_scanned(trace)`：按 `(probe, target)` 去重、同键取 `max(scanned)`（`scanned` 只取决于 `CANDIDATE_FILES` 与索引规模，与 claim 无关；取 max 因 `prober` 用 `max(scanned, len(hits))` 收口，不会低估）。`#### 查过 N 处` 的 N **保持累加口径不变**（既有「概览 = 明细之和」守卫照旧），仅在 `distinct < total` 时紧跟一行 `- 其中不同位置 {distinct} 处（同一探测项被多条需求重复扫描时只计一次）`。实测 elench-cpp `spec`：`查过 13893 处（5 条需求，10 类探测项）` + `其中不同位置 5614 处`。六份夹具中五份两数相等（零影响），`fx-spec` 为 36 vs 18 故重刷。

## 4. 文件名含 `archive` 是否该排除（建议优先级 P2，需决策）

**位置**：`src/gap_engine/index.py` 的 `SKIP_DIRS` 语义（当前只匹配目录名）。

**现象**：`editors/vscode/python/archive_specs.py` 仍作为入口证据出现。第一轮 P1-3 修的是**目录**，文件名不在范围内（这是刻意的，避免误伤正常文件）。

**验收口径**：先给结论再动手——若认为该文件是归档脚本，需要在契约里写清「文件名前缀/后缀规则」，并补一条 `test_index.py` 用例；若认为不该排除，就在本条下写「保持现状」并说明理由，避免下一轮重复讨论。

**状态（第三轮）：已结案，采纳「让仓库自己声明」而非文件名规则（`C-INDEX@3`）**。结论是不给文件名写字面规则（`archive_specs.py` 可能是正常模块，硬编码会误伤），改为 `index.py` 读取**被分析仓库根**的 `.ignore`：常量 `IGNORE_FILE = ".ignore"`，`_load_ignore` 跳过空行与 `#` 注释、去掉末位 `/`、全部转小写；含 `*` 的行走 `fnmatch`，其余按路径前缀匹配；命中目录整棵剪掉、命中文件不进 `files`；不支持 `!` 否定与父目录继承，只认仓库根一份（保证两次运行结果一致）。elench-cpp 无 `.ignore`，故 `archive_specs.py` 仍按现状进入索引——**保持现状**由被测仓库自行决定。`test_index.py` 补 5 条用例（前缀生成目录、大小写归一、`.ignore` 路径与 glob、空/仅注释 `.ignore` 无影响、`.ignore` 自身不进索引）。

## 5. 复现本轮全部结论的命令

在 `gap-engine/` 下：

```bash
python -m pytest -q                                  # 应 509 passed
python -c "
import sys; sys.path.insert(0,'src')
from gap_engine import cli
repo = r'C:/Users/haoll/Documents/deepseek-harness/default-workspace/elench-cpp'
print(cli.main(['analyze', repo, '--out', '../.tmp/stress-recheck/v4-analyze/report.md']))
print(cli.main(['spec', repo, '--spec', '../.tmp/stress-recheck/req.md', '--out', '../.tmp/stress-recheck/v4-spec/report.md']))
"
```

压测数据与三轮对照见 `reports/stress-elench-cpp.md` §6（第一轮）、§7（第二轮）、§8（第三轮）。