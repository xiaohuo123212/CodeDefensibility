# 压测记录：elench-cpp（2026-11-18）

本文是**压测留痕**，不是产品报告。结论只描述本次实测，不代表对所有仓库的普遍结论；本次**未修改任何代码**，发现项仅作记录。

## 1. 对象与方法

- 被测仓库：`C:/Users/haoll/Documents/deepseek-harness/default-workspace/elench-cpp`（作者自有项目，非第三方）
- 目录体积 301 MB，含 `build/` 下大量权限受限临时目录
- 索引实际收录 **1440** 个文本文件、**137273** 行、**40** 个测试文件
- 排除项：`build/`、`.git/` 等（`index.py:12` 的 `SKIP_DIRS`）；非白名单后缀；≥400 KB 的单文件
- 索引上限 `max_files=4000` **未触发**（1440 < 4000），本次不存在静默截断

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

| 命令 | 耗时 | 检索规模 | 退出码 |
|---|---|---|---|
| `analyze` | 12.95 s | 查过 19325 处（5 条声称，10 类探测项） | 0 |
| `spec` | 13.56 s | 查过 19195 处（5 条需求，14 类探测项） | 0 |
| `questions` | 13.61 s | — | 0 |

三次执行全部正常退出，无异常、无崩溃；`build/` 下的权限拒绝未导致中断（遍历时 `OSError` 被跳过）。耗时量级可接受，**未发现性能或稳定性问题**。

三态分布：`analyze` 有证据 4 / 没找到 1 / 有反证 0；`spec` 有证据 3 / 没找到 2 / 有反证 0。

## 3. 已复核为准确的部分

- **「依赖 0 个」是准确的**：该项目 `pyproject.toml` 写 `dependencies = []`，`package.json` 亦无 `dependencies`。这是项目自身的零依赖承诺，不是引擎漏读。
- 「40 个测试文件」「文件 1440 个 / 代码 137273 行」与独立统计一致。

## 4. 发现项

### P0-1 中文需求关键词为空时跳过相关性过滤，直接判 supported

实证（同一份清单）：

| 需求 | `classify` 类型 | `feature_terms` | 判定 |
|---|---|---|---|
| 零第三方依赖 | `feature` | `()` | **supported** |
| 提供 C++ 代码生成后端 | `feature` | `()` | **supported** |
| 支持成本与复杂度静态分析 | `feature` | `()` | **supported** |
| 提供基准测试 | `testing` | `()` | no_evidence（正确） |

机制：`matcher.py:161` 的 `feature_terms` 只认 `FEATURE_TERM_GROUPS` 固定词表，中文需求普遍命中不到；`matcher.py:329-344` 的过滤写成 `if terms:`，**词表为空即整段跳过**，于是任何满足 `claim.type in evidence.supports` 的证据都被算作支持证据，最终走到 `matcher.py:364` 的 `supported`。

「零第三方依赖」的报告里同时出现「依赖声明：0 处（扫过 3 处）」与 `supported`，判据与证据自相矛盾。

此条**不限于 C++ 仓库**：任何不含该词表词条的中文需求都可能被同样误判，属系统性误报源，直接影响误报率指标。

### P0-2 C++ 源文件不在索引白名单，却被判「有证据」

- `index.py:14-37` 的 `TEXT_SUFFIXES` 只有 Python 生态后缀，**无 `.cpp / .h / .hpp / .c / .cc`**
- 该仓库有 839 个 `.cpp`、215 个 `.h`、107 个 `.hpp`、189 个 `.c`、48 个 `.cc`、1138 个 `.eln`，**全部不进索引**
- 因此「提供 C++ 代码生成后端」的 `supported` 与任何 C++ 代码无关，是 Python 脚本里的路由命中凑出来的

### P1-3 归档目录未排除，归档脚本成为入口与证据

报告把 `_archive/2026-11-18-scripts/migrate_docs.py`、`_archive/2026-11-18-scripts/rename_ch.py` 列为入口并给出定位。`index.py:12` 的 `SKIP_DIRS` 不含 `_archive` 一类归档目录。

### P1-4 入口兜底把「最大文件」当作入口文件

`pipeline.py:143-147` 的 `_structure_entry` 取 `structure` 抽取器的首条证据路径，而该路径是「行数最多的文件」；`pipeline.py:153` 在未识别到路由时用它兜底。结果报告首段输出：

```
一句话：AI语言设计入门.md 未见路由定义；依赖 0 个；40 个测试文件。
```

把一篇中文文档当作入口文件，措辞与事实不符。

### P1-5 对非 Python 仓库的「相关实现」恒为 0

由 P0-2 直接导致：报告显示「相关实现：0 处（扫过 1440 处）」，但该仓库的实现主体是 C++ 与 `.eln`。引擎当前的覆盖面是 Python 生态仓库，对 C++ 仓库不具备「相关实现」层级的分析能力。

## 5. 结论与后续

- 性能与稳定性达标，可作为大仓库压测的正面证据（1440 文件 / 13.7 万行 / 约 13 秒 / 三次零失败）。
- 质量侧存在 2 个 P0、3 个 P1，其中 **P0-1 是系统性误报源**，优先级最高。
- 本次按决定**只留痕、不改代码**。如需修复，建议顺序：P0-1（`matcher` 相关性过滤，须变更契约并重刷六份报告）→ P1-3（归档目录排除）→ P1-4（入口兜底措辞）→ P0-2/P1-5（扩索引白名单至 C++，属产品范围扩张）。