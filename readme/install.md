# 环境与安装

## 前置条件

- Python ≥ 3.11（`python --version` 确认）
- 不需要数据库、不需要 API Key：引擎运行时**零第三方依赖**、不需要网络
- 不需要安装被测仓库的任何依赖（本工具只读文本）

## 一键安装（在仓库根执行）

```bash
pip install -e gap-engine
```

### 一键脚本（安装 + 冒烟验证）

不想逐条敲命令时，用脚本一次走完「安装 → `gap --help` → 对反证 fixture 出报告」：

```bash
bash readme/quickstart.sh          # macOS / Linux / Git Bash
```

```bat
readme\quickstart.bat              :: Windows
```

脚本只在系统临时目录写一份报告做冒烟，**不污染仓库**；报告里应出现 `结论：代码里有反证，与要求不一致` 与 `- 定位：app.py:9`。可用 `PYTHON=py-3.11`（或 `set PYTHON=py -3.11`）指定解释器。

## 验证安装

```bash
gap --help
```

应打印六个子命令：`analyze` / `questions` / `spec` / `score` / `parse-spec` / `advise`。

## 可选：演示页面依赖

本地页面需要 streamlit（`demo/app.py` 顶层 `import streamlit`）；CLI 与全部测试不需要它：

```bash
pip install -e "gap-engine[demo]"
```

不装 streamlit 也能跑 `gap spec` / `gap analyze` / `pytest`（`demo/report.py` 不 import streamlit），只影响演示页面本身。

## 推荐：虚拟环境

```bash
python -m venv .venv
```

Windows：

```bash
.venv\Scripts\activate
```

macOS / Linux：

```bash
source .venv/bin/activate
```

然后重新执行 `pip install -e gap-engine`。

## 卸载

```bash
pip uninstall gap-engine
```

## 常见问题

| 现象 | 原因与处置 |
|---|---|
| `gap: command not found` | 虚拟环境未激活；或 `pip` 与 `python` 不属于同一环境——用 `python -m pip install -e gap-engine` |
| Windows 上 `python` 不可用 | 改用 `py -3.11`，安装命令相应为 `py -3.11 -m pip install -e gap-engine` |
| 安装时提示缺少 `setuptools>=68` | 升级 pip：`python -m pip install -U pip setuptools` |