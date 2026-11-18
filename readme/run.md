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

**判定域**：只判 `performance` / `concurrency` / `feature` / `testing` 四类；`architecture` / `scale` / `security` 三类需求不判定——报告里该条写 `结论：不判定（超出判定域…）` 与 `audit effort：0 类 0 处`，不输出「查到 / 查过没找到」，不进三态计数、不计入覆盖率与 `## 未覆盖`；概览另起一行 `- 其中 N 条超出判定域，不判定`（N 为 0 时不显示）。

**排除生成目录与自定义忽略**：`build`、`build-*`、`cmake-build-*`、`CMakeFiles`、`node_modules`、`_archive` 等目录按目录名排除（大小写不敏感），生成目录里的编译器探测文件不再进索引。要把自己仓库的路径排除在外，在**被测仓库根**放一份 `.ignore`，逐行写相对路径或含 `*` 的通配（如 `docs/generated/*`、`*.min.js`）；空行与 `#` 注释被忽略，只认仓库根这一份，不支持 `!` 否定。

**「查过 N 处」的两个口径**：`#### 查过 N 处` 的 N 是按需求累加的扫描次数（等于各条 `audit effort` 之和）；同一探测项被多条需求重复扫描时，紧跟一行 `- 其中不同位置 M 处` 给出按探测项去重后的不同位置数。两数相等时不显示该行。

## 2. 自我声称核对（副模式）

```bash
gap analyze <repo>
```

真实示例：

```bash
gap analyze gap-engine/contract/fixtures/fx-feature
```

默认产物 `reports/report.md`；`--out` 改路径，`--max-claims N` 控制条数，`--json <path>` 另存结构化结果。

两种模式的报告首段「项目实际是什么」的一句话，按入口三分支输出：`{入口} 暴露 {n} 个路由` / `{入口} 未见路由定义` / `未识别到启动入口`。未识别到启动入口时显示 `未识别到启动入口`，不再把行数最多的文件当作入口文件。`spec` 模式多行段的 `入口：` 行与这句话同口径：只列真正带路由定义的文件，没有路由就写 `未识别到启动入口`，不再出现「入口列了三个文件、一句话却说没识别到入口」的自相矛盾。


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

### 三种输入方式

页面顶部的「输入方式」单选提供三种入口，另有一个可选的需求清单输入框（留空则用仓库 README 的自我声称）：

| 输入方式 | 控件 | 说明 |
| --- | --- | --- |
| 服务器路径 | 文本框 | 填服务器上已存在的仓库目录（原有用法，行为不变） |
| 上传 zip | zip 文件上传框 | 上传一个仓库 zip，服务端解压到临时目录后对账 |
| GitHub URL | 文本框 | 填 `https://github.com/<owner>/<repo>`，服务端浅克隆后对账 |

**zip 需满足的约束**（不满足时页面直接给出可读错误，不会抛未捕获异常）：

- 上传体积 ≤ 20 MB，解压后累计 ≤ 200 MB，条目数 ≤ 2000；
- 不含符号链接，不含绝对路径、`..` 路径段或盘符（防 zip-slip 写穿临时目录）；
- 若压缩包里**只有一个顶层目录**，会自动下钻进该目录对账（GitHub 自动生成的 `repo-main/` 这类包直接可用）。

**GitHub URL 的约束**：只接受 `https://github.com/<owner>/<repo>` 形式（可带 `.git` 后缀）的公开仓库；`http://`、`git@` 写法、其他域名、带用户名或端口的地址都会被拒绝。服务端执行 `git clone --depth 1`，超时 120 秒，失败时把 git 的报错摘要显示在页面上。

三种输入都在服务端临时目录内处理，请求结束即删除，不写进程 cwd、不写仓库目录；点「对账」之前页面不做任何 IO。

页面展示的报告正文与 CLI 落盘内容逐字一致（`demo/report.py` 只是复用 `pipeline`，不二次加工文案）。

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

## 9. AI 推演（可选，默认关闭）

AI 只在判定**之后**做推演，不进三态、不产定位；两条命令默认都不联网，加 `--llm` 且配置了 `GAP_LLM_API_KEY` 才会调用模型（未配置时产物明确写「未调用 AI」）。引擎仍是零运行时依赖。

**B 段：把需求清单固化为 JSON，并让模型为不可判定条目写出可验收判据**（产物：`out/spec.json`，`schema` 为 `gap-spec@1`）

```bash
gap parse-spec gap-engine/contract/fixtures/fx-contradicted/requirements.md --out out/spec.json
# 真正调用模型：为每条「不可判定」需求生成一条可验收判据
GAP_LLM_API_KEY=<key> gap parse-spec gap-engine/contract/fixtures/fx-contradicted/requirements.md --out out/spec.json --llm
```

判据规则：只有 `decidable: false` 的条目会调用模型，每条恰好一次（fx-spec 的 5 条里恰 1 条「高性能」不可判定 → 恰好 1 次调用）；模型返回的首个非空行会截断到 200 字符后写入该条 `suggestion`，返回空或调用失败则保留规则建议，`items` 的 `text` / `line` / `decidable` 不受影响。参考值：`P95 < 300ms 或 QPS ≥ 500` 会被模型改写成类似 `P95 < 300ms 且错误率 < 1%` 的判据。判据一旦落盘就固化，后续对账只读该文件、不再重算，因此同一份清单两次解析逐字节一致。

**A 段：给 `no_evidence` 条目生成推演建议**（产物：`out/advice.md`）

```bash
gap advise gap-engine/contract/fixtures/fx-contradicted --spec gap-engine/contract/fixtures/fx-contradicted/requirements.md --out out/advice.md
```

要真正调用模型时，在 `advise` 末尾追加 `--llm`（`GAP_LLM_BASE_URL` / `GAP_LLM_MODEL` / `GAP_LLM_TIMEOUT` 可选，兼容 OpenAI 接口）：

```bash
GAP_LLM_API_KEY=<key> gap advise <repo> --spec <requirements.md> --out out/advice.md --llm
```

产物说明：`out/spec.json` 的 `text` / `line` / `decidable` 只来自规则解析，`decidable: false` 条目的 `suggestion` 在 `--llm` 时改由模型给出可验收判据并随 JSON 落盘固化——固化后同一份清单两次解析逐字节一致，后续对账可只依赖该文件复现条目集合与判据；`out/advice.md` 的每条建议都标 `> AI 推演（非证据，不产生定位，不改变三态结论）`，无凭据时整份文件只有 `- 未调用 AI（未配置 GAP_LLM_API_KEY 或未加 --llm），本批次无推演建议。`。两条命令都**不写** `reports/` 下既有文件，六份 `reports/fx-*.md` 不受影响。退出码：成功 `0`；spec 读取失败或清单为空 `2`；`advise` 的仓库不存在 `1`。

**进度反馈（只走 stderr，不影响产物）**：真模型单条建议约 3.5s，多条时等待期间终端没有输出，容易以为卡死。`parse-spec` 与 `advise` 都支持 `--progress` / `--no-progress`，不加开关时按 `stderr.isatty()` 自动判定：交互终端显示逐条进度，管道、重定向与 CI 自动静默。每完成一条就地刷新为 `[2/2] 生成建议：提供数据可视化 ... 3.52s`，`advise` 标注「生成建议」、`parse-spec` 标注「生成判据」。进度**只写 stderr**：`--out` 产物字节与不加开关时逐字节一致，stdout 仍只有 `spec: {path}` / `advice: {path}`。需要在不带终端的 CI 里观察进度时显式加 `--progress`：

```bash
GAP_LLM_API_KEY=<key> gap advise <repo> --spec <requirements.md> --out out/advice.md --llm --progress
```

## 产物在哪

`gap-engine/reports/` 下六份报告，由对应 fixture 跑出，与 CLI 输出逐字一致（`tests/test_fixtures.py` 守卫）：

`fx-concurrency.md` / `fx-feature.md` / `fx-testing.md` / `fx-spec.md` / `fx-challenge.md` / `fx-contradicted.md`

## 安全说明

引擎只读文本：不执行、不导入、不安装被测仓库的任何代码；上传或分享报告前请自查其中是否含有真名、学号或密钥。