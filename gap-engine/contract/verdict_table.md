# 三态判定表（verdict_table）

判定纪律的唯一入口。任何结论只能落在这三行之一，构造 `Verdict` 时即被校验。

| status | 含义 | locator | search_trace | coverage | question_priority 示例 |
| --- | --- | --- | --- | --- | --- |
| `supported` | 仓库里有证据支持该 claim | **必须非空** | 应记录（可为空） | `full` / `partial` | `supported + high → 0` |
| `contradicted` | 仓库里有证据反驳该 claim | **必须非空** | 应记录（可为空） | `full` / `partial` | `contradicted + medium → 5` |
| `no_evidence` | 查过但没找到能判定的证据 | 必须为 `None` | 空时必须 `coverage == none`；非空时 `partial` / `none` | `partial` / `none` | `no_evidence + medium → 8`；`no_evidence + low → 10` |

## 拒绝路径（抛出 `ValueError`，前缀 `verdict.invariant:`）

| 输入 | 消息 |
| --- | --- |
| `supported` 且 `locator is None` | `verdict.invariant: supported requires locator` |
| `contradicted` 且 `locator is None` | `verdict.invariant: contradicted requires locator` |
| `no_evidence`、`search_trace=[]` 且 `coverage != none` | `verdict.invariant: no_evidence without search_trace requires coverage none` |
| `status` 不是三态之一 | `verdict.invariant: unknown enum value (...)` |

## 优先级映射

`raw = STATUS_WEIGHT[status] + CONFIDENCE_WEIGHT[confidence]`，
`question_priority = int((raw - 2) * 2.5 + 0.5)`。

| status \ confidence | high | medium | low |
| --- | --- | --- | --- |
| `supported` | 0 | 3 | 5 |
| `contradicted` | 3 | 5 | 8 |
| `no_evidence` | 5 | 8 | 10 |

同分按 `claim_id` 升序，不引入第二排序键。