# 评测 · 引擎质量（人工真值标注）

> 路径说明：本目录在交付 zip 内位于 `project/评测-引擎质量/`，在源码仓库内位于 `对账引擎/评测-引擎质量/`。
> 下文的复跑命令均以**源码仓库根**为工作目录（样本源码 `.tmp/gh-samples/` 与四个 tarball 不入包，需自行解压）。
>
> **判据版本：`C-MATCHER@10`（当前代码）**。本目录所有数字均为 @10 实测；@9 的数字只在
> `anchor-neg-10.md`（历史对照）、`spec-neg-*-v4.md`（@9 的 30 条版报告）与各文件明确标注「@9」
> 的对照行里出现。引用任何比率都必须带版本号。

本目录是 `readme/README.md`「引擎质量实测（人工真值标注，N 明确）」一节的原始产物：
需求清单（`req-*.md`）、引擎跑出的对账报告（`spec-*.md`）、逐条人工真值标注（`anchor-*.md`）。
文中每个比率都能在本目录的 anchor 表里逐条对到条目与代码行。

## 一、样本构成与条数

真实现样本（声称取自各库 README/文档自述，真值逐条到代码确认）：

| 库 | 声称数 | 需求来源 | 引擎报告（当前） | 真值标注 |
|---|---|---|---|---|
| filelock | 20 | `docs/index.rst`「Lock Types」「Platform Support」 | `spec-filelock-20-v6.md`（当前）；`spec-filelock-20-v5.md`（@9 对照）、`-v3.md`（@8 对照） | `anchor-filelock-20.md` |
| itsdangerous | 5 | `README.md:7-13` | `spec-itsdangerous-v6.md` | `anchor-itsdangerous.md` |
| markupsafe | 4 | `README.md:5-9,22-27` | `spec-markupsafe-v6.md` | `anchor-markupsafe.md` |
| blinker | 3 | `README.md:3-4,24-25` | `spec-blinker-v6.md` | `anchor-blinker.md` |
| **合计** | **32** | — | — | `anchor-all-32.md`（汇总） |

反证样本（反向构造，30 条，13 + 5 + 10 + 2）：

| 库 | 条数 | 需求清单 | 引擎报告（当前） | 真值标注 |
|---|---|---|---|---|
| filelock | 13 | `req-neg-filelock.md` | `spec-neg-filelock-v5.md` | `anchor-neg-30.md` |
| blinker | 5 | `req-neg-blinker.md` | `spec-neg-blinker-v5.md` | `anchor-neg-30.md` |
| itsdangerous | 10 | `req-neg-itsdangerous.md` | `spec-neg-itsdangerous-v5.md` | `anchor-neg-30.md` |
| markupsafe | 2 | `req-neg-markupsafe.md` | `spec-neg-markupsafe-v5.md` | `anchor-neg-30.md` |
| **合计** | **30** | — | — | — |

10 条版的 @9 记录保留在 `anchor-neg-10.md`（报告 `spec-neg-*-v3.md`），仅作历史对照，**数字不与本页混算**。

## 二、真值判定方法

**逐条到代码里找实现证据，不看文档自述。** 证据具体到文件与行号，写在 `anchor-*.md` 每条记录的
「代码证据」列。反证样本的真值则取自代码里**明写的「不支持」声明**（如 `asyncio.py:317`
「Sync context manager entry is not supported」），再把该能力反过来写成肯定句当需求。

标注只看被测仓库源码，不参考引擎输出；引擎结论由 `gap spec` 实际运行产出后与真值比对，
不凭印象填写。

## 三、六组数字及其分母（`C-MATCHER@10`）

| # | 指标 | 数值 | 分母 | 分母怎么来的 |
|---|---|---|---|---|
| 1 | precision（32 条真实现样本） | **8/8 = 100%** | 8 | 引擎下了确定判断的条数 = 有证据 8 + 有反证 0；`no_evidence` 与「不判定」不进分母 |
| 2 | recall（32 条真实现样本） | **8/32 = 25.0%** | 32 | 样本全部 32 条声称；按可判 27 条口径则 **8/27 = 29.6%**（27 = 32 − 5 条不判定） |
| 3 | 反证召回（30 条真反证样本） | **1/30 = 3.3%** | 30 | 样本全部 30 条；判成 `contradicted` 的 1 条 |
| 4 | 唯一定位（30 条真反证样本） | **1/1 = 100%** | 1 | 分母 = 引擎报出反证的条数（只 1 条），不是 30 |
| 5 | 反向错误（30 条真反证样本） | **6/30 = 20.0%** | 30 | 真 `contradicted` 被判成 `supported` 的条数 |
| 6 | 漏报（30 条真反证样本） | **23/30 = 76.7%** | 30 | 真 `contradicted` 被判成 `no_evidence` 的条数 |

32 条真实现样本的引擎结论：有证据 **8** / 没找到证据 **19** / 有反证 **0**，另 **5** 条不判定
（4 条 `out_of_scope` + 1 条不可验收）。列校验：8 + 19 + 0 + 5 = 32。

30 条真反证样本的引擎结论：有反证 **1** / 有证据 **6** / 没找到证据 **23**。
列校验：1 + 6 + 23 = 30。

## 四、口径定义

- **supported（有证据）**：引擎在被测仓库里找到与需求对应的实现证据并给出定位。
- **no_evidence（没找到证据）**：未找到证据。**不等于「没实现」**——它只说明本轮检索没命中。
- **contradicted（有反证）**：只在代码里存在显式否定声明、且与需求相关时给出。
- **不判定**：判定域预检或可验收性预检拒答，分两种——`out_of_scope`（安全类，按设计不判）与
  不可验收（需求没有可检验的验收标准）。两种必须分开报，不能合并成一个「不适用」。
  判定三态只有 `supported / contradicted / no_evidence`；「不判定」是独立位，统计时单列，不混进三态。
- **precision** = 判对条数 / 引擎下了确定判断的条数（supported + contradicted）。`no_evidence` 与「不判定」不进分母。
- **recall** = 有证据条数 / 样本条数（可判口径时分母扣掉「不判定」条数）。
- **反向错误** = 真 contradicted 被判成 supported 的条数 / 反证样本条数；它与「漏报」方向相反，必须分开报。
- 甲组七指标（认可率 / 定位率 / 漏报率 / 误报率 / 说不清率 / 未覆盖率 / 无法证伪异议率）
  需要需求提出人回执，本目录**不产出**这些数字，一律 `N=?`，禁止估算。

## 五、复跑与复算命令

样本源码不在本目录（体积与许可原因），复跑前需有解压后的源码副本。本仓库内使用
`.tmp/gh-samples/<lib>/`（由 `tox-dev-filelock.tar.gz`、`itsdangerous.tar.gz`、
`pallets-markupsafe.tar.gz`、`jek-blinker.tar.gz` 解压得到）。`gap` 由 `gap-engine/pyproject.toml`
的 `[project.scripts]` 安装（`pip install -e gap-engine`）。

在**仓库根**执行（下列命令即本目录八份报告的生成命令，产物与目录内 `spec-*.md` 逐字一致）：

```bash
gap spec .tmp/gh-samples/filelock      --spec 对账引擎/评测-引擎质量/req-filelock-20.md     --out .tmp/label/spec-filelock-20-v6.md
gap spec .tmp/gh-samples/itsdangerous  --spec 对账引擎/评测-引擎质量/req-itsdangerous.md   --out .tmp/label/spec-itsdangerous-v6.md
gap spec .tmp/gh-samples/markupsafe    --spec 对账引擎/评测-引擎质量/req-markupsafe.md     --out .tmp/label/spec-markupsafe-v6.md
gap spec .tmp/gh-samples/blinker       --spec 对账引擎/评测-引擎质量/req-blinker.md        --out .tmp/label/spec-blinker-v6.md
gap spec .tmp/gh-samples/filelock      --spec 对账引擎/评测-引擎质量/req-neg-filelock.md   --out .tmp/label/spec-neg-filelock-v5.md
gap spec .tmp/gh-samples/blinker       --spec 对账引擎/评测-引擎质量/req-neg-blinker.md    --out .tmp/label/spec-neg-blinker-v5.md
gap spec .tmp/gh-samples/itsdangerous  --spec 对账引擎/评测-引擎质量/req-neg-itsdangerous.md --out .tmp/label/spec-neg-itsdangerous-v5.md
gap spec .tmp/gh-samples/markupsafe    --spec 对账引擎/评测-引擎质量/req-neg-markupsafe.md --out .tmp/label/spec-neg-markupsafe-v5.md
```

没有全局 `gap` 命令时等价写法（在 `gap-engine/` 下）：

```bash
PYTHONPATH=src python -c "import sys;from gap_engine.cli import main;sys.exit(main())" spec ../.tmp/gh-samples/itsdangerous --spec ../对账引擎/评测-引擎质量/req-itsdangerous.md --out ../tmp-rerun.md
```

本目录所有分布数字可用一条命令复算（无需 `gap` 入口，直接调 `pipeline.analyze_spec`）：

```bash
python .tmp/diag/recompute_at10.py     # 同时输出 .tmp/diag/recompute_at10.json
```

它按「需求文件 → `pipeline.analyze_spec` → 统计 `v.status.value`」重算 32 条与 30 条两组分布，
并把 `reason == OOS_REASON` 的条目从 `no_evidence` 中拆出来单列为 `out_of_scope`，
不可验收条目由 `spec.parse` 的 `decidable=False` 单独计数。

单条报告里可复算的抓取点：`## 需求可判定性预检`（可判定/不可验收条数）、
`## 概览` 的「有证据 N 条 / 没找到证据 N 条 / 有反证 N 条」，以及每条 `结论：` 行
（`contradicted` 条目另有 `- 定位：` 行）。

## 六、`C-MATCHER@10` 相对 @9 改了什么（一句话）

新增**正证据的最低形态与参数覆盖**：`import` 行、`tests/` 下的文件和未提及声称参数的 `def` 签名不再算有效正证据，
声称里带参数时证据行还必须命中全部参数组——因此同一批样本的 `supported` 从 30 条版的 18 降到 6、
从 32 条版的 12 降到 8（细节与逐条验收口径见 `gap-engine/contract/CONTRACT.md` 的 `C-MATCHER@10` 一节）。

## 七、两条样本偏置（必须一起讲）

1. **32 条真实现的真值全取自作者自述。** 文档写「有」，代码里再逐条找证据确认，所以这批样本
   只能衡量「能不能找到证据」，**测不到「能不能识别未实现」**——未实现的能力本来就不在样本里。
2. **30 条反证只覆盖「代码明写不支持」这一种反证形态**（四库穷举显式否定语句与显式 `raise`）。隐式缺失
   （功能不存在且代码里没有任何否定声明）完全没有样本，因此 1/30 = 3.3% 不能外推为「引擎的反证能力」。

配套结论：precision 100% 的分母只有 8；主要短板是**漏报 19 条**，不是误报。

**反向错误率对判据版本极度敏感**：同一批 30 条反证样本，@9 时反向错误 18/30 = 60.0%
（报告 `spec-neg-*-v4.md`，已随包提供，可逐条复算），@10 后降到
6/30 = 20.0%（同一批声称、同一批需求文件，差异只来自判据版本）。所以引用该指标必须带版本号，
不能把它当作引擎的固定能力值；与 `anchor-neg-10.md` 里 @9 的 2/10 = 20% 也不能跨版本混算（分母与版本都不同）。

## 八、filelock 20 条版本对照

`spec-filelock-20-v1` → `v2` → `v3` → `v5` → `v6`，同一批 20 条声称，引擎五版：

| 版本 | 引擎 | 有证据 | 没找到证据 | 有反证 | precision | recall |
|---|---|---|---|---|---|---|
| v1 | `C-EXTRACTOR@7` | 4 | 9 | 7 | 4/11 = 36.4% | 4/20 = 20.0% |
| v2 | `@8`（前四类） | 8 | 9 | 3 | 8/11 = 72.7% | 8/20 = 40.0% |
| v3 | `@8`（六类，`spec-filelock-20-v3.md`） | 10 | 9 | 1 | 10/11 = 90.9% | 10/20 = 50.0% |
| v5 | `@9`（`spec-filelock-20-v5.md`） | 11 | 9 | 0 | 11/11 = 100% | 11/20 = 55.0% |
| **v6（当前）** | `@10`（`spec-filelock-20-v6.md`） | **7** | **13** | **0** | **7/7 = 100%** | **7/20 = 35.0%** |

「有证据 / 没找到证据 / 有反证」五版依次为 **4/9/7 → 8/9/3 → 10/9/1 → 11/9/0 → 7/13/0**。
@10 的 4 条降级（#4 可取消的 acquire、#11 SoftFileLease 心跳声明、#12 on_compromise 回调、
#19 自定义 executor）逐条原因见 `anchor-filelock-20.md`；它们都是「证据形态不合格」（`tests/` 文件、
类声明行），不是词表问题。另有 9 条（#1、#2、#5、#9、#10、#14、#15、#16、#17）在五版里恒为没找到证据，
是真证据本身不含探测词面的已知残留短板。

**v4 与 v3 逐字相同，是副本，不得引用**（`spec-filelock-20-v4.md` 未放入本目录）。
反证样本 v1/v2 产物同理只在 `anchor-neg-10.md` 的「三次运行对比」里作历史记录，对外口径一律引用
@10 的 `spec-neg-*-v5.md`。

## 九、目录清单（36 个文件）

标注 7：`anchor-all-32.md`、`anchor-filelock-20.md`、`anchor-itsdangerous.md`、`anchor-markupsafe.md`、
`anchor-blinker.md`、`anchor-neg-30.md`、`anchor-neg-10.md`（@9 历史对照）

需求清单 8：`req-filelock-20.md`、`req-itsdangerous.md`、`req-markupsafe.md`、`req-blinker.md`、
`req-neg-filelock.md`、`req-neg-blinker.md`、`req-neg-itsdangerous.md`、`req-neg-markupsafe.md`

引擎报告 20：
- 当前（`@10`）8：`spec-filelock-20-v6.md`、`spec-itsdangerous-v6.md`、`spec-markupsafe-v6.md`、
  `spec-blinker-v6.md`、`spec-neg-filelock-v5.md`、`spec-neg-blinker-v5.md`、
  `spec-neg-itsdangerous-v5.md`、`spec-neg-markupsafe-v5.md`
- 历史对照 9：`spec-filelock-20-v5.md`（@9）、`spec-filelock-20-v3.md`（@8）、
  `spec-neg-filelock-v3.md`、`spec-neg-blinker-v3.md`、`spec-neg-itsdangerous-v3.md`（@9 的 10 条版）、
  `spec-neg-filelock-v4.md`、`spec-neg-blinker-v4.md`、`spec-neg-itsdangerous-v4.md`、
  `spec-neg-markupsafe-v4.md`（@9 的 30 条版，用于复算本节反向错误 18/30 = 60.0% 的 @9 值）
- 无版本后缀的 `spec-itsdangerous.md`、`spec-markupsafe.md`、`spec-blinker.md` 与对应 `-v6.md`
  **逐字相同**（`@10` 后不变），保留作旧路径引用；引用时以 `-v6.md` 为准。

说明 1：`README.md`（本文件）