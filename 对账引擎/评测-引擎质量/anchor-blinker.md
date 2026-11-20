# blinker 3 条声称的标注结果

真值判定方式：逐条到代码里找实现证据，不采信 README 自述。
需求来源：`blinker/README.md:3-4`（分发系统与订阅）、`README.md:24-25`（特定 sender / 任意 sender）。
引擎报告：`spec-blinker-v6.md`（`C-MATCHER@10` 产物，与本目录 `spec-blinker.md` 逐字相同）。
标注结论：**3 条全部有真实实现**，真值均为 `supported`，真 `contradicted` 为 0 条。
**`C-MATCHER@10` 后不变**：复算结果仍为 supported 0 / no_evidence 2 / 不可验收 1（0+2+1=3），与 @9 完全相同，故本文件逐条结论未改。

| # | 声称 | 引擎结论 | 真值 | 判定 | 代码证据 |
|---|---|---|---|---|---|
| 1 | 提供快速的事件分发系统 | 不判定（无法验收：要求 P95 < 300ms 或 QPS ≥ 500） | supported（分发实现存在；「快速」为性能定性，代码不可证） | 不判定（拒答） | `src/blinker/base.py:204-253` `Signal.send` 遍历 `receivers_for` 并调用接收者、收集返回值；`:255-303` `send_async`；`__init__.py:1-17` 导出 `Signal` / `signal` / `Namespace`。仓库内无基准/压测代码，速度本身无代码证据 |
| 2 | 任意数量的订阅者可订阅事件 | no_evidence | supported | 漏报 | `base.py:87-88` `_by_receiver` / `_by_sender` 为 `defaultdict(set)`；`:78-82` `receivers` 为 dict；`:91-139` `connect` 只做 id 登记、无数量上限；`:117-118` 双向登记 |
| 3 | 接收者可订阅特定 sender 或任意 sender | no_evidence | supported | 漏报 | `base.py:18` `ANY = Symbol("ANY")`、`:21` `ANY_ID = 0`；`:91` `connect(..., sender=ANY)`；`:108` `sender_id = ANY_ID if sender is ANY else make_id(sender)`；`:326-345` `receivers_for` 把 `_by_sender[ANY_ID]` 与 `_by_sender[sender_id]` 取并集 |

## 统计

| 口径 | 数量 | 占 3 条 |
|---|---|---|
| 有证据（supported） | 0 | 0% |
| 没找到证据（no_evidence） | 2 | 66.7% |
| 有反证（contradicted） | 0 | 0% |
| 不判定（可验收性预检挡回，未进入三态） | 1 | 33.3% |
| 判对 | 0 | 0% |
| 漏报 | 2 | 66.7% |
| 误报 | 0 | 0% |

口径定义：判对 =「引擎给出的确定结论且与真值一致」/ 总数；漏报 = 真 supported 判成 `no_evidence`；误报 = 真 supported 判成 `contradicted`；不判定 = 引擎按判定域/可验收性预检整条拒答，不计入三态，也不计入判对/漏报/误报。

二分类（把「有证据」与「有反证」都算作引擎下了确定判断）：

| 指标 | 计算 | 结果 |
|---|---|---|
| precision | 判对数 / 确定判断数 = 0 / 0 | 无定义（引擎下了 0 条确定判断，N/A） |
| recall | 判对数 / 真 supported 数 = 0 / 3 | 0% |
| 反证专项 | 真 contradicted 0 条，引擎报出 0 条 | 不适用（无真反证样本） |

## 共同根因分析（2 条漏报，1 条拒答）

1. **「订阅者 / sender」这类领域词匹配不到实现标识符**
   - 真实机制是 `receivers`（订阅者）、`_by_sender` / `_by_receiver`（索引）、`ANY` / `ANY_ID`（任意 sender 的哨兵）。声称里的「任意数量」「特定 sender 或任意 sender」没有一个能直接落到这些名字上，两条都退化为 `no_evidence`。
2. **分发逻辑被 `receivers_for` 拆走，`send` 体内看不到「订阅」**
   - `send` 只做迭代调用（`:242`、`:292` 调用 `self.receivers_for(sender)`），「谁被订阅、订阅了几个」全在 `connect` + `receivers_for` 里。按单函数/单文件打分的探测方式容易漏掉这种跨方法闭环。
3. **第 1 条被可验收性预检挡回是合理的**
   - 报告第 9 行要求「P95 < 300ms 或 QPS ≥ 500」，库内没有任何基准代码，所以引擎不开三态、直接判「无法验收」在逻辑上站得住。代价是本库 1/3 声称不进入评测：对以性能为卖点的库，这一条永远测不到检索能力。
4. **纯库项目没有「入口/路由」**（全局性）
   - 报告「未识别到启动入口」，「路由/入口」「依赖声明」两类探测恒为 0，5 类里只有 3 类有效。

## 真 contradicted 说明

本库 3 条声称里**不存在真 `contradicted`**。第 1 条的「快速」属于无法用代码证伪也无法证实的定性修饰，按任务口径（有实现逻辑即 `supported`）仍记为 `supported`，但速度本身不计入真值证据。反证识别能力仍未被本样本覆盖。