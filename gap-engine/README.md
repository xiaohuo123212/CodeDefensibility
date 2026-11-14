# gap-engine

对账引擎：输入一份需求清单（或 README / 交付说明里的自我声称）和一个代码仓库，
逐条对账成 `supported` / `contradicted` / `no_evidence` 三态结论，并给出可复现的证据定位、追问与补齐建议。

## 当前状态（D4）

**已实现**：

- 数据模型 `Claim` / `Evidence` / `Verdict` / `SearchProbe` / `Locator`，含 `authority`（`external` / `self`）与三态不变量；`Verdict.rounds` 是**真实字段**（实际跑过的检索轮数，不再是硬编码 `1`）
- 8 个规则抽取器（`deps` / `entry` / `concurrency` / `tests` / `bench` / `artifact` / `config` / `structure`）
- Claimer（抽声称 + 七类分类）、Prober、Matcher（三态判定）、**Challenger（规则版，见下节）**、Renderer（markdown 报告）
- CLI：`gap analyze`、`gap questions`、`gap spec`
- 需求清单解析 + 需求可判定性预检（无法验收的条目逐条给改写建议）
- 报告两段：`## 需求可判定性预检`（共 N 条 / D 条可判定 / K 条无法验收）、`## 项目实际是什么`（规模 / 入口 / 依赖 / 测试）
- **多轮换假设检索**（`prober.ALTERNATE_PLANS` + `pipeline` 挑战循环）：`performance` / `concurrency` 第 2 轮加查「压测结果文件」（`artifact` 抽取器），`testing` 第 2 轮加查「覆盖率产物」；循环只升不降、证据与轨迹累加、`max_rounds` 钳制 1..3、第 1 轮已 `supported` 的条目不进循环；报告逐条段出现 `换假设：N 轮（第 1 轮查预设来源，其后换假设重搜）`

**未实现**（roadmap，见报告"局限"段）：

- `--claims --spec` 双模式（同时读需求清单与自我声称）
- Healer / Verifier 生成补齐物并跑通
- `contradicted` 产出（没有充分反证时一律不下断言）
- CI 门禁、IDE 悬浮

## Challenger（规则版）——已实现的部分与边界

**已实现**：检索层的**换假设重搜**。`no_evidence` 的条目进入第 2 轮，换成"结果/产物文件"这一类来源再查一遍（`performance` / `concurrency` 查压测结果，`testing` 查覆盖率产物），新证据必须能落到 `file:line` 才允许把结论升为 `supported`。

**边界（材料里不许拔高）**：

- 轮次策略是**表驱动、有限、可枚举**的（`ALTERNATE_PLANS`，每类至多 1 个备用假设，硬上限 3 轮），**不做 LLM 反证、不做多 Agent 对话**——否则同一仓库两次跑会给出不同轨迹，`search_trace` 就失去"可复核"的意义
- 只针对 `performance` / `concurrency` / `testing` 三类定义第 2 轮；`feature` / 架构 / 规模 / 安全类总轮数恒为 1
- 只升不降：已 `supported` 的直接返回，不进入循环；认为误报时只能提交证据复核，不能直接降级

**产物证据**：`reports/fx-challenge.md` —— `换假设：2 轮（第 1 轮查预设来源，其后换假设重搜）`、证据定位 `loadtest/report.log:2`、结论从第 1 轮 `no_evidence` 升为 `supported`。

## 目录结构

```
gap-engine/
├── build.sh                 # 轻量编译检查（compileall src + tests）
├── pyproject.toml           # 包定义与 pytest 配置
├── README.md
├── src/gap_engine/          # 运行时零第三方依赖
│   ├── __init__.py
│   ├── schema.py            # Claim / Evidence / SearchProbe / Verdict / Locator + 6 个枚举
│   ├── claimer.py           # 自我声称抽取 + 七类分类
│   ├── spec.py              # 需求清单解析 + 可判定性预检 + 转 Claim(authority=external)
│   ├── index.py             # 仓库索引（文件读取与缓存）
│   ├── extractors/          # 8 个规则抽取器，各自独立可测（含 artifact：结果/产物文件里的测量痕迹）
│   ├── prober.py            # ALTERNATE_PLANS + 分轮检索（plan/run 带轮次）
│   ├── matcher.py           # 三态判定 + 置信度（rounds 透传）
│   ├── pipeline.py          # analyze_repo / analyze_spec 编排 + 挑战循环（max_rounds 钳制）
│   ├── renderer.py          # markdown 报告（analyze / spec 两种）
│   ├── metrics.py           # 指标计算
│   ├── priority.py          # compute_question_priority / sort_key
│   ├── trace.py             # TraceSummary / summarize / headline
│   ├── baseline.py          # 先验普遍性表（PREVALENCE）
│   └── cli.py               # gap analyze / questions / spec
├── contract/
│   ├── CONTRACT.md          # 人可读契约
│   ├── verdict_table.md     # 三态判定表
│   └── fixtures/            # 回归基线（三个微型仓库，只读）
│       ├── fx-concurrency/  # 声明"支持 500 并发用户"，无压测证据
│       ├── fx-feature/      # 声明"支持 Excel 导出"，有 /export 路由与 openpyxl
│       └── fx-testing/      # 声明"测试覆盖率 80%"，无覆盖率报告
└── tests/
    ├── test_schema.py / test_priority.py / test_trace.py
    ├── test_claimer.py / test_index.py / test_extractors.py
    ├── test_prober.py / test_matcher.py / test_metrics.py
    ├── test_spec.py         # 需求解析 + 预检 + authority
    ├── test_fixtures.py     # fixture 固定事实 + 端到端
    ├── test_report_math.py  # 报告数字与段落结构
    └── test_cli.py          # 三个子命令
```

## 用法

```bash
# 主模式：需求核对
gap spec <repo> --spec <requirements.md> [--out reports/<repo>-spec.md]

# 副模式：从仓库 README 抽声称
gap analyze <repo> [--out reports/report.md]
gap questions <repo> --top 10
```

需求清单是 Markdown 列表（`- ` / `* ` / `+ ` / `1. ` / `1) ` / `- [ ] ` 开头），重复行去重；
解析不出条目时 `gap spec` 以退出码 2 报错，不生成空报告。

## fixture 说明

三个 fixture 都是自包含的微型仓库（各自带 README，代码总量 < 60 行，无真实个人信息
与密钥，`app.py` 仅在 `if __name__ == "__main__":` 下监听），用来固定三条主路径的
期望判定：

| fixture | 声明 | 期望三态 | 关键证据面 |
| --- | --- | --- | --- |
| `fx-concurrency` | 支持 500 并发用户 | `no_evidence` | 只有 `workers = 4`，无 locust/k6/ab/benchmark |
| `fx-feature` | 支持 Excel 导出 | `supported` | `@app.get("/export")` + `openpyxl` 依赖 |
| `fx-testing` | 测试覆盖率 80% | `no_evidence` | 有测试与 coverage 配置，无覆盖率报告 |

fixture 一经后续任务消费即冻结，修改需提升契约版本号。

## 本地运行

```bash
python -m venv .venv && . .venv/Scripts/activate   # Windows: .venv\Scripts\activate
pip install -e .
pip install pytest
pytest                                              # 预期：全部通过
bash build.sh                                       # 仅编译检查
```