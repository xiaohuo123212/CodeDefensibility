# fx-testing

测试覆盖率 80%。

## 内容

| 文件 | 说明 |
| --- | --- |
| `src/calc.py` | 两个纯函数 |
| `tests/test_calc.py` | 三个单元用例 |
| `pyproject.toml` | 项目元数据与 coverage 配置 |

## 本地运行

```bash
pip install pytest
pytest
coverage run -m pytest
```