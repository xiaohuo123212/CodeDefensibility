# fx-concurrency 回归期望

## 用途

抽取器与 Matcher 的回归基线：固定"有配置、无测量"的并发缺口形态。

## 被断言的事实

- 声称句固定为 `支持 500 并发用户`，写在 `README.md` 中，且该文件不含元描述词
- `gunicorn.conf.py` 含 `workers = 4`
- 不存在 locust / k6 / ab / benchmark 文件
- `app.run(...)` 只在 `if __name__ == "__main__":` 下出现
- 期望判定：`no_evidence`（有配置，无测量）