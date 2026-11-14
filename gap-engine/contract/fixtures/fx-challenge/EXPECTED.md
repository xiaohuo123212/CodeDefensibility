# fx-challenge 回归期望

## 用途

多轮换假设（C-PROBER@5 / C-PIPELINE@4）的端到端回归基线：第 1 轮的预设探测项查不到
"500 并发"的测量痕迹，第 2 轮换成"压测结果文件"才在 `loadtest/report.log` 里找到，
用于演示"换假设重搜"如何把误判压下去。

`requirements.md` 是外部需求清单，不作为声称来源；本文件不参与声称抽取。

## 被断言的事实

- 「支持 500 并发用户」：第 1 轮 `no_evidence`（代码里无压测脚本/并发原语/worker 配置），
  第 2 轮升级为 `supported`，`rounds == 2`，`locator.file` 为 `loadtest/report.log`，
  `reason` 含「第 2 轮换假设」
- 该条的 `search_trace` 累加两轮 probe，第 2 轮 probe 名「压测结果文件」出现在 trace 中
- 「用户登录」：第 1 轮即 `supported`，`rounds == 1`，不进入挑战循环
- 报告逐条段出现 `换假设：2 轮（第 1 轮查预设来源，其后换假设重搜）`
- 报告局限段出现 `本批对未找到的条目最多换假设 2 轮检索（k = max(v.rounds)）。`
- 概览 `查过 {total} 处` 等于各条 `audit effort` 处数之和