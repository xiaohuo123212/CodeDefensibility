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

## 产物在哪

`gap-engine/reports/` 下六份报告，由对应 fixture 跑出，与 CLI 输出逐字一致（`tests/test_fixtures.py` 守卫）：

`fx-concurrency.md` / `fx-feature.md` / `fx-testing.md` / `fx-spec.md` / `fx-challenge.md` / `fx-contradicted.md`

## 安全说明

引擎只读文本：不执行、不导入、不安装被测仓库的任何代码；上传或分享报告前请自查其中是否含有真名、学号或密钥。