# 码道应用总结

**先说结论**：码道（CodeArts Agent）在本项目里承担的是**实现与验证的执行者**，判定规则由人先冻结成契约、再交给它执行。哪一步用了、哪一步没用，下面逐项写。

## 逐环节

| 环节 | 码道做了什么 | 证据位置 |
|---|---|---|
| **契约编写** | 把三态定义、优先级映射、`search_trace` 形状、索引口径写成 design 里的 `C-*` 契约，再拆成带 `write_set` 的任务；改代码前先改契约 | `.codeartsdoer/plans/gap-engine-d0/` … `gap-engine-d6/` 的 `design.md` 与 `task.md` |
| **抽取器** | 实现 9 个规则抽取器（`deps` / `entry` / `concurrency` / `tests` / `bench` / `artifact` / `negation` / `config` / `structure`），每个独立可测 | `gap-engine/src/gap_engine/extractors/`、`tests/test_extractors.py` |
| **判定** | 三态判定与 `contradicted` 三条件（显式否定声明 / 关键词相关 / 能贴 `file:line`）；挑战循环只让 `no_evidence` 进第 2 轮 | `matcher.py`、`pipeline.py`、`tests/test_matcher.py` |
| **测试与回归** | 全量用例 + fixture 报告逐字守卫 + `max_rounds` 钳制断言 | `gap-engine/tests/`、`tests/test_fixtures.py`、`tests/test_report_math.py` |
| **报告渲染** | 固定段序的报告；局限段按实际检索轮数动态生成；`contradicted` 有独立结论文案 | `renderer.py`、`tests/test_report_math.py` |
| **文档同步** | 口径变更（Challenger 规则版、`contradicted` 已实现、`Verdict.rounds` 真字段）逐份回写 README / 施工图 / 契约 | `gap-engine/contract/CONTRACT.md`、《施工图-对账引擎》§1.5.1 / §1.6 |
| **演示前端** | 纯函数 `demo/report.py` + 页面壳 `demo/app.py`，页面正文与 CLI 逐字一致 | `gap-engine/demo/`、`tests/test_demo.py` |

## 留痕

- **按天记录**：`codearts_proof/daily/D0.md` 起，D0–D6 连续归档，每天含「目标 / prompt 原文 / AI 输出摘要 / 人工纠偏」四段。
- **计划与契约**：`.codeartsdoer/plans/gap-engine-d*/`，每批的 `design.md`（需求 + 验收不变量 + 契约）与 `task.md`（任务、write_set、依赖）都在。
- **诚实标注**：`prompt 原文` 段落为空是有意为之，由本人从会话记录原样粘贴；AI 整理的段落已标 `generated`，不事后编造。

## 不夸大

- 没有用码道做**自动部署**，也没有多 Agent 自动跑生产流程。
- **LLM 不参与判定**：分类歧义不做消解，规则优先；这也是"同一仓库两次跑轨迹一致"的前提。
- 质量指标（作者认可率、误报率）需要 5 份需求清单的作者回执后统计，本文档不写任何估算数字。
- `Healer` / `Verifier`（生成补齐物并验证）仍是 roadmap，未在本批交付。