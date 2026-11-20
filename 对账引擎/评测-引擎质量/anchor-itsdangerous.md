# itsdangerous 5 条声称的标注结果

真值判定方式：逐条到代码里找实现证据，不采信 README 自述。
需求来源：`itsdangerous/README.md:7-13`（正文两段）。
引擎报告：`spec-itsdangerous-v6.md`（`C-MATCHER@10` 产物，与本目录 `spec-itsdangerous.md` 逐字相同）。
标注结论：**5 条全部有真实实现**，真值均为 `supported`，真 `contradicted` 为 0 条。
**`C-MATCHER@10` 后不变**：复算结果仍为 supported 0 / no_evidence 3 / 不判定 2（0+3+2=5），与 @9 完全相同，故本文件逐条结论未改。

| # | 声称 | 引擎结论 | 真值 | 判定 | 代码证据 |
|---|---|---|---|---|---|
| 1 | 支持把数据传给不可信环境并安全取回 | 不判定（超出判定域：安全类） | supported | 不判定（拒答） | `src/itsdangerous/serializer.py:309-320` `dumps` 序列化后签名；`:328-343` `loads` 先验签再 `load_payload`；`url_safe.py:72-83` URL 安全包装 |
| 2 | 数据以密码学方式签名，确保 token 未被篡改 | 不判定（超出判定域：安全类） | supported | 不判定（拒答） | `signer.py:63` `hmac.new(key, msg=value, digestmod=...)`；`:28` `hmac.compare_digest` 验签；`:182-207` 三种密钥派生（concat/django-concat/hmac）；`serializer.py:340-343` 验签失败抛 `BadSignature` |
| 3 | 支持自定义数据序列化方式 | no_evidence | supported | 漏报 | `serializer.py:194` 构造参数 `serializer`；`:216-219` 存为 `self.serializer`（缺省 `default_serializer`）；`:276` `dump_payload` 透传 `serializer_kwargs`；`:243-269` `load_payload` 支持逐次覆盖序列化器 |
| 4 | 支持按需压缩数据 | no_evidence | supported | 漏报 | `url_safe.py:55-69` `dump_payload` 用 `zlib.compress`，且仅当 `len(compressed) < len(json) - 1` 才采用（即「按需」）；`:44-51` 读取时按前缀 `.` 决定 `zlib.decompress` |
| 5 | 支持添加并自动校验时间戳 | no_evidence | supported | 漏报 | `timed.py:45-51` `TimestampSigner.sign` 追加 base64 时间戳；`:138-153` `unsign` 按 `max_age` 判过期并抛 `SignatureExpired`；`:170-175` `TimedSerializer` 默认使用 `TimestampSigner`；`:185-220` 加载时自动校验 |

## 统计

| 口径 | 数量 | 占 5 条 |
|---|---|---|
| 有证据（supported） | 0 | 0% |
| 没找到证据（no_evidence） | 3 | 60% |
| 有反证（contradicted） | 0 | 0% |
| 不判定（超出判定域，未进入三态） | 2 | 40% |
| 判对 | 0 | 0% |
| 漏报 | 3 | 60% |
| 误报 | 0 | 0% |

口径定义：判对 =「引擎给出的确定结论且与真值一致」/ 总数；漏报 = 真 supported 判成 `no_evidence`；误报 = 真 supported 判成 `contradicted`；不判定 = 引擎按判定域预检整条拒答，不计入三态，也不计入判对/漏报/误报。

二分类（把「有证据」与「有反证」都算作引擎下了确定判断）：

| 指标 | 计算 | 结果 |
|---|---|---|
| precision | 判对数 / 确定判断数 = 0 / 0 | 无定义（引擎下了 0 条确定判断，N/A） |
| recall | 判对数 / 真 supported 数 = 0 / 5 | 0% |
| 反证专项 | 真 contradicted 0 条，引擎报出 0 条 | 不适用（无真反证样本） |

## 共同根因分析（3 条漏报 + 2 条超域拒答）

1. **实现用词与声称用词不同**（第 3、4、5 条的漏报主因）
   - 「自定义数据序列化方式」→ 实现叫 `serializer` / `serializer_kwargs` / `load_payload`，源码里没有「序列化方式」这种表述。
   - 「按需压缩」→ 实现是 `zlib.compress` 加长度比较，源码里没有 `compress as needed` 这种短语（README 才有）。
   - 「时间戳自动校验」→ 实现叫 `TimestampSigner` / `max_age` / `SignatureExpired`，「时间戳」只出现在 docstring，探测短语与标识符对不上。
2. **安全类需求被整条判定域排除**（第 1、2 条）
   - 报告第 33、43 行给出的理由是「架构 / 规模 / 安全类需求不在本次判定范围」。但这两条恰好是本库最核心、也最容易找到证据的（`signer.py` 的 HMAC、`serializer.py` 的签名/验签闭环）。按库的整体判定域一刀切，等于对密码学库关闭了主功能评测。
3. **纯库项目没有「入口/路由」**（全局性）
   - 报告「项目实际是什么」段写「未识别到启动入口」，5 类探测项里「路由/入口」「依赖声明」两类对无 entry point 的库恒为 0，实际只有 3 类在起作用。

## 真 contradicted 说明

本库 5 条声称里**不存在真 `contradicted`**（无「明确声明不支持或做了相反行为」的项）。因此本库与 filelock 样本一样，只能衡量「能不能找到证据」，测不到「能不能识别未实现」。任务交付说明中「三库让评测第一次覆盖识别未实现的能力」这一预期，在 itsdangerous 上未成立，须在四库汇总里如实标注。