# 开源组件说明

## 运行时依赖：零

`pip install -e gap-engine` 不会下载任何第三方运行时包——`pyproject.toml` 里 `dependencies = []`。

实际只用 Python 标准库：`argparse` / `json` / `sys` / `re` / `dataclasses` / `pathlib` / `fnmatch` / `collections` / `functools` / `enum` / `tomllib` / `typing`。

这就是"零运行时依赖"的含义：不是"依赖很少"，是**一个都不装**。换台干净机器只要 Python ≥ 3.11 就能跑。

## 构建与开发期组件

| 组件 | 版本约束 | 用途 | 许可证 |
|---|---|---|---|
| setuptools | ≥ 68 | 构建后端（`pyproject.toml` 的 `build-system`） | MIT |
| pytest | ≥ 8 | 测试（`dev` 可选依赖） | MIT |
| streamlit | ≥ 1.30 | 本地演示页面（`demo` 可选依赖） | Apache-2.0 |

## 说明

- **streamlit 只服务演示页面**：`demo/app.py` 用它画界面；`demo/report.py` 不 import streamlit，因此没装 streamlit 也能跑全部测试与 CLI。
- **不含任何第三方源码拷贝**：`gap-engine/src/` 全部为本项目实现。
- **不用 tree-sitter、不调 LLM、不调云 API**：抽取与判定都是规则实现（`extractors/` + `matcher.py`），这也是同一仓库两次运行给出同一条轨迹的前提。
- **不安装被测仓库的依赖**：被测代码只被当作文本读取。
- 报告与文档中不含第三方项目的原始代码。