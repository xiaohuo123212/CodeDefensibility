# 三态判定表（verdict_table）

判定纪律的唯一入口。任何结论只能落在这三行之一，构造 `Verdict` 时即被校验。

| status | 含义 | locator | search_trace | coverage | question_priority 示例 |
| --- | --- | --- | --- | --- | --- |
| `supported` | 仓库里有证据支持该 claim | **必须非空** | 应记录（可为空） | `full` / `partial` | `supported + high → 0` |
| `contradicted` | 仓库里有证据反驳该 claim | **必须非空** | 应记录（可为空） | `full` / `partial` | `contradicted + medium → 5` |
| `no_evidence` | 查过但没找到能判定的证据 | 必须为 `None` | 空时必须 `coverage == none`；非空时 `partial` / `none` | `partial` / `none` | `no_evidence + medium → 8`；`no_evidence + low → 10` |

## `contradicted` 的判定条件（C-MATCHER@4）

`contradicted` 优先级最高：三条同时满足时，在任何 `supported` / `no_evidence` 分支之前给出。

1. 相关证据中存在 `snippet` 含否定标记的条目。标记表唯一来源是
   `src/gap_engine/extractors/negation.py` 的 `NEGATION_MARKERS`（不复制第二份）。
2. 该条目的 `file` / `snippet` 与需求文本的显著词有交集（`matcher.claim_terms`
   提取，英文 ≥3 字符，中文按停用词切分后 2–6 字）。
3. 该条目有可用行号（`line is not None`）。**全部无行号时不得判 `contradicted`**，
   降回原流程（`locator` 为空无法定位，反证不可核）。

`anchor` 取满足条件的证据中 `strength` 最高者，`locator` 指向它；`evidence_ids`
仍收录全部相关证据（支持与反证都在，报告可核）。`reason` 先写「代码里有反证：…」，
若同时存在非否定证据，再追加被推翻的支持痕迹条数。

`contradicted` 在第 1 轮即定论、**不进入挑战循环**（C-PIPELINE@5），`rounds` 恒为 1；
`gap_label` 返回「该改」，`fix` / `question` 使用反证专用文案。

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