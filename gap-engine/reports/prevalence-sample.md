# prevalence 实测样本说明（N=10）

本文件记录一次针对 GitHub 公开仓库的 prevalence 实测：按固定查询与固定筛选标准取 10 个
Python 应用型仓库，逐个跑 `gap analyze --json`，再由 `tools/measure_prevalence.py`
聚合为 `reports/prevalence.json`。目的是把判定管线里 `baseline.PREVALENCE` 的**先验**
换成一份可复现的**实测**物料。

## 0. 口径与合规声明

- 本文所有指标写作 `N=?`，`N` 为实际统计到的可判定声称条数；**禁止估算**。
- 只输出**聚合比例**，不点名任何项目的具体缺陷或对账结论。
- 表中 `full_name` 与 commit sha **仅用于复现**，不对单个项目作公开结论；不记录个人作者信息。
- 本轮 `reports/prevalence.json` 是**独立物料**：判定管线不读取它，`is_prevalent`
  仍使用 `baseline.PREVALENCE` 先验表（详见 §7）。
- 未因结果好坏替换任何样本；跳过项均为口径条件不符（§4）或网络故障后重试成功（§5）。

## 1. 固定查询

```
https://api.github.com/search/repositories?q=language:python+stars:20..500+size:%3C5000+topic:webapp+fork:false&sort=stars&order=asc&per_page=100
```

- 返回 `total_count = 104`，取第一页 100 条。
- 排序固定为 `stars asc`（星数从低到高），因此返回顺序稳定、可复现。
- 按 API 返回顺序逐个检查条件，取**前 10 个符合条件者**，不因分析结果替换。

## 2. 筛选标准（逐条执行，未做事后调整）

| 条件 | 检查方式 |
| --- | --- |
| 来源 GitHub 公开仓库 | 选自上述 search API 结果 |
| `language:python` | API 查询条件 |
| 必须含 README.md | 克隆后检查根目录存在 `readme.md`（大小写不敏感） |
| 必须含 requirements.txt 或 pyproject.toml | 克隆后检查根目录存在任一 |
| 仓库体积 < 5 MB | API 查询条件 `size:<5000`（单位 KB） |
| star 20–500 | API 查询条件 `stars:20..500` |
| 应用型/课程设计型（README 有功能自述），排除框架与库 | 读 README 正文判定：有可运行产品/功能自述则纳入；库、框架、模板脚手架、清单型仓库、README 功能自述不足（< 约 500 字符）则跳过 |

## 3. 执行时间

- 执行日期：2026-11-15（本地时间 01:33–01:43，Windows git-bash）
- 环境：Python 3.14.7，git 2.55.0.windows.3
- 临时克隆目录：`gap-engine/../.tmp/github-sample/`（不入库）

## 4. 样本清单（10 个）

`claims` 为该仓库跑 `gap analyze --json`（`--max-claims` 取默认值 5）后 JSON 里的
`claims` 条数；sha 为 `git clone --depth 1` 后默认分支 HEAD。

| 序号 | full_name | 默认分支 | commit sha | star | size(KB) | 依赖声明 | claims |
| --- | --- | --- | --- | --- | --- | --- | --- |
| S01 | booleanhunter-tech-blog/kartpool | master | d5bec147dd050363f71ac1950cf05457cd453710 | 20 | 43 | requirements.txt | 0 |
| S02 | MainakRepositor/WhatsApp-Sentiment-Analyzer | master | 5f3cf202f687f60f0cb8106f788cd6b4857e9e1c | 21 | 121 | requirements.txt | 0 |
| S03 | BnademOverflow/FaceKit | main | 889f9fa7c3bebb602ba4dd2e7f8400981c1963c6 | 21 | 778 | requirements.txt | 0 |
| S04 | SiddhantSadangi/st_deepgram_playground | main | b8bdf0e1ccb170e35f0c41d0b4cbbcd14e54e52a | 21 | 2307 | requirements.txt | 1 |
| S05 | g-paras/sentiment-analysis-api | master | 048e1413a7397cf7c190f2e7111462781a95f36a | 21 | 1751 | requirements.txt | 0 |
| S06 | GaganpreetKaurKalsi/SentimentAnalysis-Streamlit | main | 754c9a70e2d91bcda9cdfd144db78a52650d7355 | 22 | 187 | requirements.txt | 1 |
| S07 | Lynnesbian/FediBooks | master | ebdc384454246a330ef954c670b2cafb88943c71 | 22 | 320 | requirements.txt | 0 |
| S08 | dovvnloading/Qwen3-TTS-1.7B | main | 87823fda09d3c8070a5d2ebb8d656aae149da91a | 23 | 473 | requirements.txt | 1 |
| S09 | anshk1234/molecule-visualiser | main | 6089d8d25b9c84defdee73004a36d45a08da83f4 | 23 | 791 | requirements.txt | 0 |
| S10 | lwatsondev/pste | main | b20e592dfad4c7d652f68f5f3c7650640167a1b9 | 24 | 1544 | pyproject.toml | 0 |

`full_name` 与 sha 仅供复现，不对单个项目作结论。

## 5. 按返回顺序的跳过记录

以下条目按 API 返回顺序位于 S10 之前或之间，均按 §2 条件跳过；跳过后继续向下取，直到
凑满 10 个（最后一个合格者为返回顺序第 18 条）。跳过原因均属口径条件不符，不是挑样本。

| 返回顺序 | full_name | 跳过原因 |
| --- | --- | --- |
| 1 | jmcph4/pytrade | 根目录无 requirements.txt / pyproject.toml |
| 7 | rmalav15/DHSGAN | 根目录无 requirements.txt / pyproject.toml |
| 10 | Salaah01/django-email-signals | 可复用 Django 包（库），非应用型 |
| 11 | jnmclarty/pyenvdiff-lib | 根目录无 README.md |
| 12 | adilsaid64/reddit-project | README 仅 98 字符，无功能自述 |
| 14 | akshitvjain/restaurant-finder-featureReviews | 根目录无 requirements.txt / pyproject.toml |
| 16 | SuperBruceJia/pytorch-flask-deploy-webapp | 根目录无 requirements.txt / pyproject.toml |
| 17 | dfurtado/pyterrier | 根目录无 requirements.txt / pyproject.toml（且为微框架，非应用型） |
| 19 | Correia-jpv/fucking-awesome-web-security | 根目录无 requirements.txt / pyproject.toml（清单型仓库） |
| 22 | MrConsoleka/aiogram-miniapp-template | 模板/脚手架，非应用型 |
| 24 | tushar2704/Streamlit-Magic-Cheat-Sheets | 文档/速查表集合，非应用型 |
| 25 | opengeos/geospatial-dataviz | README 仅 404 字符，功能自述不足 |
| 26 | Tomansion/Vue3-FastAPI-WebApp-template | 根目录无 requirements.txt / pyproject.toml（模板） |
| 27 | devrajkataria/Credit-Card-Fraud-Detection-ML-WebApp | 根目录无 requirements.txt / pyproject.toml |

**网络故障与重试**：执行期间 GitHub 出现一次约 10 分钟连接中断，导致返回顺序
12、13、15、16、17、18、19、20、21、22、23、24、25、26、27、28、29 的浅克隆首次失败
（`Failed to connect to github.com:443` / `Connection was reset` / `Empty reply from server`）。
中断恢复后对这些仓库原样重试（最多 3 次）：克隆全部成功，随后按 §2 条件重新判定
（其中 16、17、19、26、27 因无依赖声明或属清单/模板继续跳过，12 因 README 无功能自述跳过，
其余按返回顺序纳入）。**因此本轮不存在"因 clone 失败而替换样本"的情况**；
`analyze` 阶段 10 个样本全部成功，无报错替换。

## 6. 复现命令

```bash
# 1) 取样：固定查询，按返回顺序记录 full_name / star / size
curl -s -H "Accept: application/vnd.github+json" \
  "https://api.github.com/search/repositories?q=language:python+stars:20..500+size:%3C5000+topic:webapp+fork:false&sort=stars&order=asc&per_page=100"

# 2) 浅克隆（临时目录不入库），按 §2 条件筛选，取前 10 个
git clone --depth 1 https://github.com/<full_name>.git .tmp/github-sample/S01
git -C .tmp/github-sample/S01 rev-parse HEAD      # 记录默认分支 commit sha

# 3) 逐个分析（--out 必须显式给到临时目录，避免写入仓库 reports/）
cd gap-engine
python -m gap_engine.cli analyze ../.tmp/github-sample/S01 \
  --json ../.tmp/github-sample/S01.json --out ../.tmp/github-sample/S01.md
# ……S02 … S10 同法执行

# 4) 聚合实测比例（--compare 打印实测 vs 先验）
python tools/measure_prevalence.py \
  --analysis ../.tmp/github-sample/S01.json ../.tmp/github-sample/S02.json \
             ../.tmp/github-sample/S03.json ../.tmp/github-sample/S04.json \
             ../.tmp/github-sample/S05.json ../.tmp/github-sample/S06.json \
             ../.tmp/github-sample/S07.json ../.tmp/github-sample/S08.json \
             ../.tmp/github-sample/S09.json ../.tmp/github-sample/S10.json \
  --out reports/prevalence.json --compare
```

## 7. 实测结果

`_source = measured`，`_n_projects = 10`。可判定声称总量 `N=?`（禁止估算，以
`reports/prevalence.json` 中各类型的 `n_claims` 为准），逐类如下：

| 类型 | 实测 prevalence | N（可判定声称数） | 先验 |
| --- | --- | --- | --- |
| performance | 100.0% | N=1 | 30% |
| concurrency | 0.0% | N=0 | 50% |
| architecture | 0.0% | N=0 | 60% |
| feature | 100.0% | N=2 | 90% |
| scale | 0.0% | N=0 | 40% |
| testing | 0.0% | N=0 | 80% |
| security | 0.0% | N=0 | 50% |

> 表中 `architecture` / `scale` / `security` 三行的 `0.0%` 与 `N=0` **不具含义**：它们属不判定域，
> 结构性不参与统计（见 §9），不得对外引用为「实测 0%」。

`--compare` 原样输出：

```
performance：实测 100.0%（N=1）｜先验 30%
concurrency：实测 0.0%（N=0）｜先验 50%
architecture：实测 0.0%（N=0）｜先验 60%
feature：实测 100.0%（N=2）｜先验 90%
scale：实测 0.0%（N=0）｜先验 40%
testing：实测 0.0%（N=0）｜先验 80%
security：实测 0.0%（N=0）｜先验 50%
```

### 局限（必读）

1. **可判定声称样本量极小**：10 个项目只抽取到 3 条可判定声称（`N=?`，禁止估算）。
   其中 `N=0` 的五类必须拆开看，性质不同、不得混为一谈：
   - `architecture` / `scale` / `security`：**结构性不判定**。它们不在判定域内
     （`contract/scope.md`：识别七类、只判四类），`n_claims` 恒为 0，与样本无关。
   - `concurrency` / `testing`：**样本未覆盖到可判定声称**。两者都在判定域内，只是本批
     10 个仓库的 README 没有产出这两类可判定句子，属于样本现象、可用更多样本改善。

   `prevalence` 在 `N=0` 时按脚本定义为 `0.0`，**这不是"实测该类型不普遍"的证据**。
2. **抽取口径所致**：声称抽取只认含能力/量化标记词的句子（`claimer` 的
   `CAPABILITY_MARKERS` / `QUANT_MARKERS`），本批样本 README 多为短列表式功能描述，
   句子不含这些标记词，故多数仓库 `claims = 0`。这属于管线当前口径的真实结果，本轮
   未修改抽取器。
3. **本轮不接入判定**：`reports/prevalence.json` 未被 `baseline.py` / `pipeline.py`
   读取；`is_prevalent` 仍用先验表。若后续接入，需单独立项并同步六份 fixture 报告与
   一致性守卫。
4. **N=10 只表示项目数**：`_n_projects = 10` 是参与聚合的 analysis 文件数，不代表
   声称条数；对外表述应写「10 个应用型仓库、可判定声称 N=? （禁止估算）」。
## 8. 第二轮止损实验（A 组 N=10）

第一轮 10 个项目只抽到 3 条可判定声称。第二轮试图用「更高 star 区间 + README 长度过滤」
把声称总量做上去，并预设止损条件：**A 组可判定声称总数 < 10 即停止，不跑 B/C**。

### 8.1 A 组查询（原样）

```
https://api.github.com/search/repositories?q=language:python+stars:500..20000+size:%3C5000+fork:false&sort=stars&order=desc&per_page=100
```

- 返回 `total_count = 10815`，取第一页 100 条，排序固定 `stars desc`。
- 筛选条件 = §2 全部条件，追加「README 正文 >= 1500 字符」。
- 实际扫描到**返回顺序第 43 条**才凑满 10 个应用型合格者：期间 13 个仓库因无依赖声明、
  无 README、README 不足 1500 字符，或属清单/模型研究仓库被跳过（属口径条件不符，不是挑样本）。

### 8.2 A 组样本（S11–S20）

`claims` 为该仓库 `gap analyze --json`（`--max-claims` 默认 5）后的条数；sha 为
`git clone --depth 1` 后默认分支 HEAD。

| 序号 | full_name | 默认分支 | commit sha | star | size(KB) | 依赖声明 | claims | 声称类型 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| S11 | mxrch/GHunt | master | 5ee893929c51c7a8a665b199bbae04ce85a662b4 | 19848 | 538 | pyproject.toml | 0 | — |
| S12 | ActivityWatch/activitywatch | master | b1dbd358ef6e284baa33aa075a885716538f1e1a | 19626 | 1876 | pyproject.toml | 1 | security×1 |
| S13 | LibreTranslate/LibreTranslate | main | 84cd56c061a7ba3955b49efdaee2ac54dcbca07f | 17705 | 4243 | pyproject.toml | 0 | — |
| S14 | MatrixTM/MHDDoS | main | bf66ccc3bbadd50dc5fed6955ba315fa8a1721b9 | 17021 | 2042 | requirements.txt, pyproject.toml | 0 | — |
| S15 | binux/pyspider | master | 897891cafb21ea5b4ac08e728ad2ea212879f7fa | 16744 | 4171 | requirements.txt | 1 | feature×1 |
| S16 | twintproject/twint | master | e7c8a0c764f6879188e5c21e25fb6f1f856a7221 | 16410 | 4578 | requirements.txt | 0 | — |
| S17 | FlareSolverr/FlareSolverr | master | cc2224b21e31c09a713eb25690a8e8dcdf50d8d8 | 16226 | 1358 | requirements.txt | 1 | feature×1 |
| S18 | coderamp-labs/gitingest | main | 4e259a02fe72115bee538271622f1234a81c8e1a | 16139 | 1486 | requirements.txt, pyproject.toml | 0 | — |
| S19 | mvt-project/mvt | main | c9190e05ef4c67df6407bc8b2adbd904954b9388 | 16039 | 4614 | pyproject.toml | 4 | security×2, feature×2 |
| S20 | Datalux/Osintgram | master | a560498be79a3bf40d7f3b203ad174661b8e81e7 | 15625 | 4964 | requirements.txt | 0 | — |

`full_name` 与 sha 仅供复现，不对单个项目作结论。

### 8.3 七类 n_claims 分布与止损判定

原始 claims 共 **7 条**：`feature` 4 条（分布于 3 个仓库）、`security` 3 条（分布于 2 个仓库）。
`security` 不在判定域，被 `is_judgeable` 过滤，**不计入统计**；可判定声称 = **4 条**。

| 类型 | n_claims（统计口径） | 是否判定域 |
| --- | --- | --- |
| performance | 0 | 是 |
| concurrency | 0 | 是 |
| feature | 4 | 是 |
| testing | 0 | 是 |
| architecture | 0 | 否（结构性不判定） |
| scale | 0 | 否（结构性不判定） |
| security | 0（原始 3 条被 `is_judgeable` 过滤） | 否（结构性不判定） |

**止损触发：可判定声称 4 < 10。** 因此 B 组（`topic:flask`）与 C 组（`topic:django`）
**未执行**，原因即止损条件命中——继续扩样本无法把可判定声称堆到可利用的规模。
A 组 10 份 analysis JSON 与聚合结果 `prev-A.json` 留在临时目录 `.tmp/github-sample2/` 备查，
`reports/prevalence.json` 未改动（仍为第一轮 N=10、`_n_projects = 10`）。

### 8.4 一条有价值的实证

A 组有 2 个真实仓库的 README 确实写出了 `security` 声称（共 3 条，成功识别），但 `security`
属不判定域，管线**如实不判、也不计入 prevalence**。这说明 `security` 的 `N=0` 不是抽取失败，
而是「识别到了但无法机械验证，所以不判」的设计结果——与 §9 一致。

## 9. 为什么只有四类可统计

依据 `contract/scope.md`（「识别七类，只判四类」）：

- **判定域（下结论的四类）**：`performance` / `concurrency` / `feature` / `testing`。
  它们有固定抽取路径，断言能落到 `file:line` 或留下可复现的搜索轨迹，因此可给出
  `supported` / `contradicted` / `no_evidence` 三态结论。
- **不判定域（识别但不判的三类）**：`security` / `architecture` / `scale`。
  识别照样做，但不下结论，也不进 `supported` / `contradicted` 的分子。

由此可得三条硬结论：

1. `prevalence.json` 里 `architecture` / `scale` / `security` 的 `n_claims` 恒为 `0` 是
   **结构性结果**（`schema.is_judgeable` 对这三类返回 `False`，聚合脚本直接跳过），
   与样本量、README 质量无关。
2. 这三行对应的 `prevalence` 字段（`0.0`）**不具含义**，对外**不得**引用为「实测 0%」。
3. `baseline.PREVALENCE` 先验表中这三类的值（`architecture` 60% / `scale` 40% /
   `security` 50%）是**残留值**：判定管线对不判定域不下结论，这三类不会走到
   `is_prevalent`，因此这些值不参与任何判定。正确处置是标注「未纳入实测」，
   而不是拿它们与实测值做对比。

`tools/measure_prevalence.py` 的 `--compare` 仍会为七类各打印一行，其中三类恒为
`实测 0.0%（N=0）`；这是脚本输出格式，不代表测量结果，引用时须按本节处理。

## 10. 两轮对照（敏感性）

| 轮次 | 项目数 | 长度过滤 | 可判定声称 | 条/项目 |
| --- | --- | --- | --- | --- |
| 第一轮 | N=10 | 无（README 仅要求存在） | 3 条（performance 1 + feature 2） | 0.3 |
| 第二轮 A 组 | N=10 | README >= 1500 字符、stars 500–20000 | 4 条（feature 4） | 0.4 |

- 过滤条件从「README 存在」收紧到「README >= 1500 字符 + 高 star」，可判定声称从
  0.3 条/项目升到 0.4 条/项目，**边际效果微弱**。
- 按此斜率，即使把 B/C 各 10 个项目跑完（合计 30 份），可判定声称也只有十余条，
  多数判定域类型仍会 `N<3`。
- 结论：**样本不是瓶颈**。瓶颈在 `claimer._CLAIM_MARKERS` 口径——`_is_claimable`
  要求句子含中文「支持 / 实现 / 提供 / 集成 / 完成 / 采用」或英文
  「provides / integrate / integrates / built with」，而真实 README 多为名词短语列表
  （`- Monthly Activity map`、`Features:` 这类），整句抽不到，于是整仓库 `claims = 0`。
- **本轮不改抽取器**：放宽标记词会改变六份 fixture 报告与 `test_fixtures.py` 的一致性
  守卫，需单独立项处理，此处仅登记为后续改进项。

## 11. 对外表述模板

以下句子可直接用于 readme 与 PPT（保留 `N=?` 占位与三类限定，**不得只报百分比**）：

> 我们在 10 个 GitHub 公开 Python 应用型仓库上做了一次可复现的 prevalence 实测：
> 判定域四类（performance / concurrency / feature / testing）共抽到可判定声称 `N=?` 条
> （禁止估算，取值以 `reports/prevalence.json` 为准），其中 performance 与 feature 的
> 声称均取得了 `supported` / `contradicted` 结论；security / architecture / scale 三类属
> 不判定域（识别但不判），**不纳入实测**，其数值不对外引用为「实测 0%」。