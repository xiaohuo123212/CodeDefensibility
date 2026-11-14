# fx-feature 回归期望

## 用途

抽取器与 Matcher 的回归基线：固定"路由 + 依赖都在、可判为有证据"的功能形态。

## 被断言的事实

- 声称句固定为 `支持 Excel 导出`，写在 `README.md` 中，且该文件不含元描述词
- `app.py` 含 `@app.get("/export")` 路由定义，函数体内调用 `openpyxl`
- `requirements.txt` 含 `openpyxl`
- `app.run(...)` 只在 `if __name__ == "__main__":` 下出现
- 期望判定：`supported`（code + dep 证据）