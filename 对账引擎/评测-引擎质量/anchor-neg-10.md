# 反证样本 10 条（反向构造）

## 构造方式

前四库 32 条声称全部取自 README 自述，真值全是「有实现」，因此测不到「能不能识别未实现」。
本样本反过来做：从四个库**代码里明写的「不支持」声明**出发，把对应能力写成肯定句当需求，
于是 10 条真值全部为 `contradicted`。

- 声称清单：`.tmp/gh-samples/req-neg-{filelock,blinker,itsdangerous}.md`（5 + 3 + 2）
- 引擎报告（最新）：`.tmp/label/spec-neg-{filelock,blinker,itsdangerous}-v3.md`
- 真值来源：逐条读代码确认，不看文档

## 结果（v3 = post-`C-MATCHER@9`）

| # | 库 | 声称 | 真值 | 引擎结论 | 引擎给的定位 | 定位对不对 |
|---|---|---|---|---|---|---|
| 1 | filelock | AsyncFileLock 支持用同步 with 语句加锁 | contradicted | **有反证** | `src/filelock/asyncio.py:317` | **对**（正是真证据那行） |
| 2 | filelock | FileLock 支持用 lifetime 参数按文件年龄强制过期 | contradicted | **有证据** | `tests/test_soft_lifetime_warning.py:204` | 反向错误（真值是不支持） |
| 3 | filelock | SoftFileLock 支持 preserve_lock_file=True 保留锁文件不删 | contradicted | **有证据** | `src/filelock/_descriptor.py:37` | 反向错误（真值是不支持） |
| 4 | filelock | 所有锁类型都支持 on_acquired 回调拿到文件描述符 | contradicted | 没找到证据 | — | — |
| 5 | filelock | 同一个锁类允许用不同参数创建多个单例实例 | contradicted | 没找到证据 | — | — |
| 6 | blinker | Signal.send 支持向异步协程订阅者发送事件 | contradicted | 没找到证据 | — | — |
| 7 | blinker | Signal.send_async 支持向同步函数订阅者发送事件 | contradicted | 没找到证据 | — | — |
| 8 | blinker | receiver_disconnected 会在弱引用接收者被回收时自动触发 | contradicted | 没找到证据 | — | — |
| 9 | itsdangerous | 签名分隔符 sep 可以自由指定为任意单字符 | contradicted | 没找到证据 | — | — |
| 10 | itsdangerous | URLSafeSerializer 加载时容忍被截断的压缩负载不报错 | contradicted | 没找到证据 | — | — |

真证据应为：

| # | 真证据位置 | 原文要点 | v3 是否命中 |
|---|---|---|---|
| 1 | `asyncio.py:317,327` | 「Sync context manager entry is not supported because lock acquisition is a coroutine」 | **命中（结论+定位都对）** |
| 2 | `_api.py:777`、`:524` | 「a native OS lock cannot be broken safely by file age」；lifetime 被忽略并告警 | 未命中（`:524` 被抽取器抑制） |
| 3 | `_api.py:613-614` | `if preserve and not supported:` + `msg = "... is not supported by ..."` | 未命中（控制流取反 + 待抛消息双重抑制） |
| 4 | `_api.py:626-627` | `on_acquired is not supported by ...: only native locks expose the lock descriptor` | 未命中（`_MESSAGE_ASSIGN_RE` 抑制） |
| 5 | `_api.py:481` | 「Singleton lock instances cannot be initialized with differing arguments」 | 未命中（`cannot` 不在否定词表） |
| 6 | `base.py:244-245` | `Cannot send to a coroutine function.` | 未命中（`cannot` 不在词表） |
| 7 | `base.py:293-295` | `Cannot send to a non-coroutine function.` | 未命中（同上） |
| 8 | `base.py:60-63` | 「This signal cannot be emitted by an automatic disconnect」 | 未命中（同上） |
| 9 | `signer.py:147-152` | sep 落在 base64 alphabet 内则抛 `ValueError` | 未命中（该行不被抽成否定声明） |
| 10 | `url_safe.py:45-52` | zlib 解压失败抛 `BadPayload` | 未命中（同上） |

## 三次运行对比（同一批 10 条，引擎三版）

| 版本 | 产物 | contradicted 判对 | 反证定位准确 | 反向错误（判成 supported） | 漏报（判成 no_evidence） |
|---|---|---|---|---|---|
| v1（`@7` 基线） | `spec-neg-*.md` | 2/10 = 20% | 0/2 = 0% | 1/10 = 10% | 7/10 = 70% |
| v2（`@8`） | `spec-neg-*-v2.md` | 3/10 = 30% | 1/3 = 33% | 0/10 = 0% | 7/10 = 70% |
| **v3（`@9`）** | `spec-neg-*-v3.md` | **1/10 = 10%** | **1/1 = 100%** | **2/10 = 20%** | **7/10 = 70%** |

**必须成对讲的代价（重要）**：

- `@8` 修好了错误定位：#1 原先被判 `supported`（反向错误），`@8` 起变成 `contradicted`，且定位就是真证据 `asyncio.py:317`。
- `@9` 把 #2、#3 从 `contradicted` 打回 `supported`。这两条原本「结论对、定位错」（`_strict.py:830` 讲 Termux 硬链接、`tests/test_util.py:613` 是 pytest 参数 id），现在定位不再指错行——但也**不再报反证**。由于真值仍是 `contradicted`，这是**反向错误从 2 类降到 0、又从 0 升到 2**的净变化：**用「少说错」换来了「敢说错的更少，但漏判也更多」**。
- 净结果：反证召回 3/10 → 1/10（下降），定位准确 1/3 → 1/1（上升），反向错误 0/10 → 2/10（上升）。
- 这 2 条翻成 `supported` 的机制不是随机：声称里写了 API 名（`lifetime` / `preserve_lock_file`），实现里确实存在同名参数与代码，所以正证据匹配成功；而真证据行仍被抽取器守卫压住。**引擎缺的是「该 API 名对这条声称的适用范围是否成立」（`FileLock` vs `SoftFileLease`、`SoftFileLock` 的支持边界），这是参数级语义判断，不是词表问题。**

## 统计（v3）

| 指标 | 数值 | 计算 |
|---|---|---|
| 反证召回（结论判对为 contradicted） | 10% | 1/10 |
| 反证定位准确 | 100% | 1/1（唯一定位就是真证据行） |
| 反向错误（真 contradicted 判成 supported） | 20% | 2/10 |
| 漏报（真 contradicted 判成 no_evidence） | 70% | 7/10 |

## 五条根因的现状

**一、中文声称与英文否定行没有词面重叠，真证据被相关性过滤掉。（仍在，7 条漏报的主因）**
`asyncio.py:317` 明写「Sync context manager entry is not supported」，而声称是「支持用同步 with 语句加锁」，
两边没有一个共同词。本轮新增 `C-MATCHER@7` 的中英实现词组后可判为相关，所以这条已救回；其余 7 条的真证据本身不含任何 `NEGATION_MARKERS`（见上表「v3 是否命中」），扩词表救不了。

**二、反证能不能被找到，取决于用户有没有把 API 名写进需求。（仍在）**
命中过的 3 条要么写了英文标识符（`lifetime`、`preserve_lock_file`），要么写了 `with` + `AsyncFileLock`；
不写 API 名的 7 条全部漏。

**三、命中的反证定位全落在无关行。（已修，`C-MATCHER@8/@9`）**
根因是 `mentions` 的 haystack 含文件路径：需求里出现 `filelock` 时 `src/filelock/` 下每一行都恒命中，
于是 `_strict.py:830`（Termux 无 `os.link`）与 `tests/test_util.py:613`（pytest 参数 id `unsupported`）被当成相关反证。
`@9` 改为路径只取文件名后，这两处不再命中；`snippet` 里的 `true`/`false` 字面量也由 `@8` 的 `_GENERIC_TERMS` 剔除。

**四、`C-EXTRACTOR@8` 的否定作用域守卫是全局抑制，会连带压掉真反证。（仍在）**
第 3 条的真证据 `_api.py:613`（`if preserve and not supported:`）与 `:614`（待抛消息）分别被
`_is_control_flow_expression` 与 `_MESSAGE_ASSIGN_RE` 抑制；第 4 条 `:626-627` 同被 `_MESSAGE_ASSIGN_RE` 抑制。
@8 让 20 条「真 supported」样本的误报从 7 降到 0，代价就是把「代码明确拒绝某选项」这一最有力的反证形态一起关掉了。
守卫与需求无关，它不知道当前这条需求正是在问那个被拒绝的选项。

**五、测试文件被当成证据源。（已修）**
第 1 条以前把 `tests/test_async_filelock_transition_admission.py:31` 算作「相关实现」，第 3 条把 pytest 参数 id
算作「否定声明」。`@8` 增加测试守卫 + `@9` 收紧路径匹配后，两处都不再命中。

## 与前四库样本的关系

- 32 条「真 supported」样本 → 衡量**误报**：precision 12/12 = 100%，recall 12/32 = 37.5%（见 `anchor-all-32.md`）。
- 10 条「真 contradicted」样本 → 衡量**反证召回**：1/10 = 10%，定位准确 1/1 = 100%，反向错误 2/10。

两个数字必须成对讲。只看前者会得出「引擎很准」，只看后者会得出「反证基本不可用」。
真实需求清单里通常既含已实现项也含未实现项，所以两个数字都要报。