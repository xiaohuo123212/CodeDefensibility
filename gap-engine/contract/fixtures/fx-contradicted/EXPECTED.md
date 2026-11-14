# fx-contradicted 回归期望

## 用途

反证判定（C-MATCHER@4 / C-RENDERER@7）的端到端回归基线：仓库里有一行显式否定声明，
与该条需求的关键词直接相关，用于演示"要求与代码冲突"时如何下断言；同一份需求清单里
另一条没有冲突，必须保持原结论。

`requirements.md` 是外部需求清单，不作为声称来源；本文件不参与声称抽取。

## 被断言的事实

- 「支持 Excel 导出」：`contradicted`，`locator.file == "app.py"`，`locator.line` 指向
  `raise NotImplementedError` 那一行，`reason` 含「反证」
- 「用户登录」：`supported`，`rounds == 1`（代码里有 `/login` 路由）
- 报告逐条段该条出现 `结论：代码里有反证，与要求不一致` 与 `- 定位：app.py:<行号>`
- 概览 `查过 {total} 处` 等于各条 `audit effort` 处数之和