# fx-testing 回归期望

## 用途

抽取器与 Matcher 的回归基线：固定"有测试、无覆盖结论"的覆盖率缺口形态。

## 被断言的事实

- 声称句固定为 `测试覆盖率 80%`，写在 `README.md` 中，且该文件不含元描述词
- `src/calc.py` 恰好 2 个函数
- `tests/test_calc.py` 恰好 3 个 `def test_` 函数
- `pyproject.toml` 含 `[tool.coverage.run]` 段
- 不存在 `.coverage` / `coverage.xml` / `htmlcov/` 覆盖率产物
- 期望判定：`no_evidence`（有测试，无覆盖结论）