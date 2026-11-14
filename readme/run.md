# 运行步骤

除明确标注 `cd gap-engine` 的步骤外，命令都在**仓库根**执行；`<repo>` 是目标仓库路径，`<requirements.md>` 是需求清单路径。安装见 [install.md](install.md)。

## 1. 需求核对（主模式）

```bash
gap spec <repo> --spec <requirements.md>
```

真实示例：

```bash
gap spec gap-engine/contract/fixtures/fx-contradicted --spec gap-engine/contract/fixtures/fx-contradicted/requirements.md
```

默认产物 `reports/<repo 名>-spec.md`，可用 `--out <path>` 指定。需求清单是 Markdown 列表（`- ` / `* ` / `+ ` / `1. ` / `1) ` / `- [ ] ` 开头）；解析不出条目时退出码为 2，不生成空报告。

## 2. 自我声称核对（副模式）

```bash
gap analyze <repo>
```

真实示例：

```bash
gap analyze gap-engine/contract/fixtures/fx-feature
```

默认产物 `reports/report.md`；`--out` 改路径，`--max-claims N` 控制条数，`--json <path>` 另存结构化结果。

## 3. 本地演示页面

演示页面依赖 streamlit，先安装：

```bash
pip install -e "gap-engine[demo]"
```

**方式一（推荐，在仓库根执行）：**

```bash
streamlit run gap-engine/demo/app.py
```

**方式二（先 `cd gap-engine`）：**

```bash
cd gap-engine
python -m demo.app
```

`demo` 包不在 setuptools 的包发现范围内，所以 `python -m demo.app` 只能在 `gap-engine/` 目录下执行；两种方式都需要已安装 streamlit（`demo/app.py` 顶层 `import streamlit`）。没有 streamlit 时请直接用 CLI（`gap spec` / `gap analyze`），CLI 不需要任何第三方包。

页面输入仓库路径与可选的需求清单路径，点「对账」后展示的报告正文与 CLI 落盘内容逐字一致（`demo/report.py` 只是复用 `pipeline`，不二次加工文案）。

## 4. 追问清单（可选）

```bash
gap questions <repo> --top 10
```

按 `question_priority` 降序输出前 N 条会被问到的问题，同分按 `claim_id` 稳定排序。

## 5. 自测

```bash
cd gap-engine
pytest
bash build.sh
```

## 6. 普遍性（prevalence）口径

缺口判定要用"这类要求在同类项目里普遍吗"。这个数有两个来源，**不得混用**：

| 来源 | 值从哪来 | 对外标注 |
|---|---|---|
| 先验表 | `gap-engine/src/gap_engine/baseline.py` 的 `PREVALENCE`（人对同类项目的经验值） | 「先验」——报告局限段固定写明「缺口判定依赖先验普遍性表（PREVALENCE），尚未用同类项目实测」 |
| 实测 | 多份 `gap analyze --json` 产物聚合出的 `reports/prevalence.json`（顶层 `"_source": "measured"`，另带 `_n_projects`） | 「实测」——必须同时给出样本数 N |

**实测的类别边界**：只有 `performance` / `concurrency` / `feature` / `testing` 四类可判定（见 `gap-engine/contract/scope.md` 的判定域）。`architecture` / `scale` / `security` 属不判定域，**不纳入实测**——它们的 `n_claims` 恒为 0，`prevalence` 字段不具含义，对外**不得**引用为「实测 0%」。当前实测结果、样本清单与两轮对照见 `gap-engine/reports/prevalence-sample.md`。

复算命令（在 `gap-engine/` 目录执行；`--analysis` 可传多份 `--json` 产物，每个被测项目一份）：

```bash
python tools/measure_prevalence.py --analysis <多份 analyze --json 产物> --out reports/prevalence.json --compare
```

`--compare` 会逐类打印「实测 x%（N=…）｜先验 y%」，便于核对偏差。

**纪律**：报告的默认值来自先验表，标「先验」；跑过上述命令后的数值才是实测，标「实测」。两者不得混用；未实测时数值必须写成 `N=?` 并标「先验」，禁止把先验值说成实测。

## 7. 回执评分（七指标）

需求提出人按条目判「对 / 错 / 说不清」并把回执整理成 JSONL 后，用 `gap score` 一次算出七个指标。每行都带分母 N；**漏报率与误报率分开成行**，不合并。

```bash
# 1) 先产出可被 score 读取的分析结果
gap analyze <repo> --json out/analysis.json

# 2) 回执 JSONL：每行一个对象
#    {"claim_id": "...", "author_verdict": "对|错|说不清", "author_evidence": "file:line 或留空"}
gap score --analysis out/analysis.json --receipts receipts.jsonl --out reports/score.md --json out/score.json
```

> 注意字段名：回执里的 `claim_id` 要填 `analysis.json` 中 `claims[].id` 的值（如 `c01`），不是 `claims[]` 里的其他字段名。填错的回执会被静默跳过，表现为 `n_valid` 小于 `n_receipts`。

输出顺序固定：认可率 / 定位率 / 漏报率（假阴性）/ 误报率（假阳性）/ 无法证伪异议率 / 说不清率 / 未覆盖率。

分母为 0 的指标记 `0.0` 并如实显示 `N=0`——**没有回执就不出数字，不估算**。`--receipts` 省略时七行仍会打印（此时依赖回执的指标均为 `N=0`）。非法行（缺 `claim_id`、裁决值不在三选一内）会被跳过，不中断。

## 8. 打包成提交包

在仓库根（含 `ppt/ video/ codearts_proof/ readme/ gap-engine/` 的那一层）执行：

```bash
python gap-engine/tools/package.py --name "对账引擎-GapEngine-<队伍名>-v1.0-<手机号>.zip"
```

产物落在 `dist/`，顶层恰为 `ppt/ project/ video/ codearts_proof/ readme/` 五个目录（`gap-engine/` 在包内改名为 `project/`），并自动排除 `.git/`、`__pycache__/`、`*.pyc`、`.env`、`build/`、`dist/` 等。若某个目录缺失，脚本会打印 `缺少交付目录：<名>` 并以退出码 2 结束。

## 产物在哪

`gap-engine/reports/` 下六份报告，由对应 fixture 跑出，与 CLI 输出逐字一致（`tests/test_fixtures.py` 守卫）：

`fx-concurrency.md` / `fx-feature.md` / `fx-testing.md` / `fx-spec.md` / `fx-challenge.md` / `fx-contradicted.md`

## 安全说明

引擎只读文本：不执行、不导入、不安装被测仓库的任何代码；上传或分享报告前请自查其中是否含有真名、学号或密钥。