# 对账引擎 · 交付说明

**一句话**：给一份需求清单和一个代码仓库，逐条回答「要求做的，代码里做了吗」——每条结论都给 `文件:行` 和搜索轨迹，查过哪里、没查到哪里。

## 交付包结构

赛事要求的五个目录与本仓库的对应关系：

| 目录 | 内容 | 本仓库位置 |
|---|---|---|
| `readme/` | 总览 / 环境与安装 / 运行步骤 / 开源组件 / 码道应用总结 | 本目录 |
| `project/` | 可运行源码（引擎 + CLI + 本地演示前端） | `gap-engine/`；口径与评测文档在 `对账引擎/` |
| `ppt/` | 答辩用 PPT（场景 / 架构 / 亮点 / 码道应用 / 指标与边界） | 页级大纲见 `ppt/PPT大纲.md`（同批交付） |
| `video/` | ≤ 3 分钟演示 | 分镜与旁白见 `video/脚本.md`（同批交付） |
| `codearts_proof/` | 码道交互留痕，按天归档 | `codearts_proof/daily/D0.md` 起 |

## 它输出什么

三态结论，不存在第四种：

| 结论 | 含义 | 必须附带 |
|---|---|---|
| `supported` | 找到支持证据 | `file:line` 定位 |
| `contradicted` | 代码里有**显式否定声明**，与要求不一致 | `file:line` 定位 |
| `no_evidence` | 我找过这些地方，没找到 | `search_trace`（查过几类、几处） |

判定域只有 `performance` / `concurrency` / `feature` / `testing` 四类；其余类型标"不判定"并写明原因。七类识别与四类判定的书面理由、以及「识别七类为什么只判四类」的答辩口径见 [`contract/scope.md`](../gap-engine/contract/scope.md)。

## 五份文档

- [install.md](install.md) —— 环境与安装（Python ≥ 3.11，零运行时依赖）
- [run.md](run.md) —— 四种运行方式：`gap spec` / `gap analyze` / `gap score` / `python -m demo.app`，外加打包命令
- [oss.md](oss.md) —— 开源组件与实际依赖清单
- [codearts.md](codearts.md) —— 码道在哪些环节被使用，以及没被使用的部分

## 30 秒验证

```bash
pip install -e gap-engine
gap --help
gap spec gap-engine/contract/fixtures/fx-contradicted --spec gap-engine/contract/fixtures/fx-contradicted/requirements.md
```

最后一条应在 `reports/` 下产出 `fx-contradicted-spec.md`，其中包含 `结论：代码里有反证，与要求不一致` 与 `- 定位：app.py:9`。

## 边界（不做什么）

- **不执行被测代码**：只读文本，不导入、不安装被测仓库的任何依赖。
- **不猜语义**：`contradicted` 只认显式否定声明（`extractors/negation.py`），不做语义推断；与需求无关的否定不算。
- **不补实现**：Healer / Verifier（生成补齐物并验证）仍是 roadmap，材料里不写成已完成。
- **指标未填**：认可率 / 误报率需要 5 份需求清单的作者回执后统计，本目录不写估算值。