# markupsafe 未实现能力声称（反向构造，用于测反证）

说明：这些声称**不是** markupsafe 文档里的真实宣称，而是把代码里明写「不支持」的限制反过来写成肯定句，
用于测量引擎能否识别未实现项。真值全部来自代码，见 `anchor-neg-30.md`。

markupsafe 功能面很窄（`escape` / `Markup` / `soft_str`），`src/markupsafe/*.py` 与 `docs/` 里
显式「不支持」语句只有下面 2 处，故本库上限为 2 条。

- [ ] Markup 的 __html_format__ 接受非空的格式说明符
- [ ] 只定义 __html__ 的类可以直接在 Markup.format 中带格式说明符使用