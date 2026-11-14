# fx-spec 回归期望

## 用途

spec 模式（需求清单驱动）的端到端回归基线：**5 条需求里 1 条无法验收、2 条有缺口**
（并发 1 条 + 可视化 1 条），用于演示"需求可判定性预检 → 项目实际是什么 → 逐条对账"的完整链路。

`requirements.md` 是外部需求清单，不作为声称来源（claimer 只读 `README*.md`），
本文件也不参与声称抽取。

## 被断言的事实

- `parse_spec` 得 5 条，`decidable` 分布为 `[True, True, True, False, True]`（第 6 行 `高性能` 不可判定，建议 `P95 < 300ms 或 QPS ≥ 500`）
- `analyze_spec` 得 `claims` 4 条、`verdicts` 4 条，`metrics` 键集合与 C-METRICS@1 一致
- 4 条 claim 的 `authority` 全为 `"external"`，`source` 依次为 `#L3` / `#L4` / `#L5` / `#L7`
- 4 条 claim 的 `type` 依次为 `[feature, concurrency, feature, feature]`（「支持 500 并发用户」属并发类）
- `支持 Excel 导出` → `Status.supported`，`locator.file` 的 basename 为 `app.py`
- `支持 500 并发用户` → `Status.no_evidence`（缺口一）
- `提供数据可视化` → `Status.no_evidence` 且 `locator is None`（缺口二）
- 报告文本含 `## 需求可判定性预检`、`P95 < 300ms`、`## 项目实际是什么`、`来源：requirements.md#L4`

## 判据外置（C-SPEC@2 / C-RENDERER@5）

- `default_criteria("支持 500 并发用户")` == `CONCURRENCY_CRITERIA`（`错误率 < 1% 且 P95 < 1s（行业惯例，需提出人确认）`）
- 报告全篇只有一行以 `- 判据：` 开头的行，位于 `### 支持 500 并发用户` 的 `该补什么：` 之后、`audit effort：` 之前
- `高性能`（不可判定，只出现在预检段）、`用户登录`、`支持 Excel 导出`、`提供数据可视化` 均不产生 `- 判据：` 行
- `- 判据：` 行不参与概览 `查过 N 处` 与 `audit effort` 计数

## 项目实际是什么（C-PIPELINE@3 / C-RENDERER@5）

- `analysis.routes` == `("GET /export", "GET /login")`，`analysis.summary` == `app.py 暴露 2 个路由；依赖 2 个（flask, openpyxl）；0 个测试文件。`
- 报告 §1 在四行事实清单之后追加 `- 一句话：…` 与 `- 路由：2 个（GET /export, GET /login）`
- 三份 pilot fixture 的报告（`fx-concurrency` / `fx-feature` / `fx-testing`）在 `## 概览` 之前同样出现 `## 项目实际是什么` 与 `- 一句话：` 行