# 反证样本 30 条（反向构造，v5 = `C-MATCHER@10` 实测）

## 构造方式

前一版 10 条（`anchor-neg-10.md`）只覆盖 filelock / blinker / itsdangerous 三库，markupsafe 为 0。
本轮在同一批四个本地库（`.tmp/gh-samples/{filelock,blinker,itsdangerous,markupsafe}/`）里穷举
`cannot | can not | not supported | unsupported | is not allowed | will be ignored | has no effect |
does not support | not implemented | 显式 raise` 等否定语句，把每处「不支持 X」反写成中文肯定句
「支持 X」当需求，于是 30 条真值全部为 `contradicted`。

- 声称清单：`对账引擎/评测-引擎质量/req-neg-{filelock,blinker,itsdangerous,markupsafe}.md`（13 + 5 + 10 + 2）
- 引擎报告（当前）：`spec-neg-{filelock,blinker,itsdangerous,markupsafe}-v5.md`（`C-MATCHER@10` 产物，本目录内）
- 真值来源：逐条读源码确认，不看文档；找不到确切行号的候选已丢弃，未凑数

### 每库上限（本轮实测）

| 库 | 条数 | 显式否定语句分布 | 上限说明 |
|---|---|---|---|
| filelock | 13 | 已有 5 条不动，新增 8 条（`asyncio.py`、`_api.py`、`_read_write.py`、`_strict.py`、`_soft.py`） | 源码仍有未采的否定语句（如 `_strict.py:830` Termux 无 `os.link`、`_soft.py:104-107` 与已有 3/4 条重复），但都是**同一能力的同类表述**，再扩会与已有条目重复，故取 13 作为本次上限 |
| blinker | 5 | 已有 3 条不动，新增 2 条（`has_receivers_for` 不做存活检查、簿记剪枝非线程安全） | 库仅 961 行，显式否定只剩 `base.py:82`「簿记不是公开 API」（兼容性限制而非功能缺失，标准偏弱，弃用），上限 5~6 |
| itsdangerous | 10 | 已有 2 条不动，新增 8 条（`signer.py`、`timed.py`、`url_safe.py`、`serializer.py`） | `signer.py:147` 的 sep 校验与 `url_safe.py:48` 的 zlib 失败已分别是第 1、2 条，其余 `raise BadSignature/BadPayload` 各对应一条，基本用尽 |
| markupsafe | 2 | 新建清单 | 功能面仅 `escape`/`Markup`/`soft_str`，`src/markupsafe/*.py` 与 `docs/` 全文只有 2 处显式不支持（`__html_format__` 非空格式说明符、`__html_format__` 必须与 `__html__` 同定义），**上限就是 2** |

合计 30 条，达成目标，不需要新增库。若要继续扩到 40+，必须引入「显式拒绝某参数组合」类库
（如 werkzeug 的 `Request.max_content_length` 限制、click 的 `Option` 互斥约束），四库本身已无新形态。

## 结果表（v5 = `C-MATCHER@10`，当前代码）

「引擎给的定位」一列取自对应报告该条的「定位：」行（仅 `contradicted` 才输出该行）；
判成「有证据」的条目取报告该条「查到」段的首条证据行。判成「没找到证据」时引擎不给定位（`locator=None`），记 `—`。

| # | 库 | 声称 | 真值 | 引擎结论 | 引擎给的定位 | 定位对不对 |
|---|---|---|---|---|---|---|
| 1 | filelock | AsyncFileLock 支持用同步 with 语句加锁 | contradicted | **有反证** | `src/filelock/asyncio.py:317` | **对**（正是真证据那行） |
| 2 | filelock | FileLock 支持用 lifetime 参数按文件年龄强制过期 | contradicted | 没找到证据 | — | — |
| 3 | filelock | SoftFileLock 支持 preserve_lock_file=True 保留锁文件不删 | contradicted | 没找到证据 | — | — |
| 4 | filelock | 所有锁类型都支持 on_acquired 回调拿到文件描述符 | contradicted | 没找到证据 | — | — |
| 5 | filelock | 同一个锁类允许用不同参数创建多个单例实例 | contradicted | 没找到证据 | — | — |
| 6 | filelock | AsyncFileLock 在 thread_local=True 时仍支持 run_in_executor=True | contradicted | 有证据 | `tasks/benchmark.py:4`（压测脚本） | 无关行（反向错误） |
| 7 | filelock | SoftFileLock 支持非默认的锁选项（如 thread_local=True） | contradicted | 有证据 | `tasks/benchmark.py:4`（压测脚本） | 无关行（反向错误） |
| 8 | filelock | FileLock 在 fork 出的子进程里可以直接复用父进程构造的实例 | contradicted | 有证据 | `src/filelock/_read_write.py:62` | 无关行（反向错误） |
| 9 | filelock | ReadWriteLock 单例允许用不同的 timeout 和 blocking 复用同一实例 | contradicted | 没找到证据 | — | — |
| 10 | filelock | preserve_lock_file=True 能阻止其它进程删除锁文件路径 | contradicted | 没找到证据 | — | — |
| 11 | filelock | fallback_to_soft 参数在 Windows 平台上同样生效 | contradicted | 没找到证据 | — | — |
| 12 | filelock | StrictSoftFileLock 的 lifetime 参数能按文件年龄清除陈旧声明 | contradicted | 没找到证据 | — | — |
| 13 | filelock | SoftFileLock 在 Windows 上释放时会立即删除锁文件 | contradicted | 有证据 | `src/filelock/_marker.py:53` | 无关行（反向错误） |
| 14 | blinker | Signal.send 支持向异步协程订阅者发送事件 | contradicted | 没找到证据 | — | — |
| 15 | blinker | Signal.send_async 支持向同步函数订阅者发送事件 | contradicted | 没找到证据 | — | — |
| 16 | blinker | receiver_disconnected 会在弱引用接收者被回收时自动触发 | contradicted | 没找到证据 | — | — |
| 17 | blinker | Signal.has_receivers_for 会排除已被回收的弱引用接收者 | contradicted | 没找到证据 | — | — |
| 18 | blinker | Signal 的簿记剪枝在多线程并发 connect/disconnect 下是线程安全的 | contradicted | 没找到证据 | — | — |
| 19 | itsdangerous | 签名分隔符 sep 可以自由指定为任意单字符 | contradicted | 没找到证据 | — | — |
| 20 | itsdangerous | URLSafeSerializer 加载时容忍被截断的压缩负载不报错 | contradicted | 没找到证据 | — | — |
| 21 | itsdangerous | SigningAlgorithm 基类自带可用的签名实现，子类无需实现 get_signature | contradicted | 有证据 | `src/itsdangerous/signer.py:15` | 同文件无关行（反向错误；真证据在 `signer.py:22`） |
| 22 | itsdangerous | Signer 支持任意自定义的 key_derivation 名称 | contradicted | 有证据 | `src/itsdangerous/signer.py:15` | 同文件无关行（反向错误；真证据在 `signer.py:213`） |
| 23 | itsdangerous | NoneAlgorithm 会生成非空的签名 | contradicted | 没找到证据 | — | — |
| 24 | itsdangerous | TimestampSigner.unsign 接受不含时间戳的签名值 | contradicted | 没找到证据 | — | — |
| 25 | itsdangerous | TimestampSigner 接受格式错误的时间戳并照常返回 | contradicted | 没找到证据 | — | — |
| 26 | itsdangerous | URLSafeSerializer 接受含非 base64 字符的负载 | contradicted | 没找到证据 | — | — |
| 27 | itsdangerous | Serializer.load_payload 在反序列化器抛异常时返回 None 而不报错 | contradicted | 没找到证据 | — | — |
| 28 | itsdangerous | Signer.unsign 接受缺少分隔符的字符串并返回空签名 | contradicted | 没找到证据 | — | — |
| 29 | markupsafe | Markup 的 __html_format__ 接受非空的格式说明符 | contradicted | 没找到证据 | — | — |
| 30 | markupsafe | 只定义 __html__ 的类可以直接在 Markup.format 中带格式说明符使用 | contradicted | 没找到证据 | — | — |

真证据应为：

| # | 真证据位置 | 原文要点 | v5 是否命中 |
|---|---|---|---|
| 1 | `asyncio.py:317`、`:327` | 「Sync context manager entry is not supported because lock acquisition is a coroutine」 | **命中（结论+定位都对）** |
| 2 | `_api.py:777`、`:524` | 「a native OS lock cannot be broken safely by file age」，lifetime 被丢弃并告警 | 未命中（@9 时判成 supported） |
| 3 | `_api.py:613-614` | `if preserve and not supported:` + 「preserve_lock_file=True is not supported by …」 | 未命中（@9 时判成 supported） |
| 4 | `_api.py:626-627` | 「on_acquired is not supported by …: only native locks expose the lock descriptor」 | 未命中 |
| 5 | `_api.py:481` | 「Singleton lock instances cannot be initialized with differing arguments」 | 未命中 |
| 6 | `asyncio.py:170` | 「run_in_executor is not supported when thread_local is True」 | 未命中（**仍判成 supported**） |
| 7 | `_api.py:661` | 「{cls} does not support non-default lock options: …」 | 未命中（**仍判成 supported**） |
| 8 | `_api.py:447` | 「Lock construction cannot continue after fork; construct a new lock in the child」 | 未命中（**仍判成 supported**） |
| 9 | `_read_write.py:517` | 「cannot be changed to timeout=…, blocking=…」 | 未命中（@9 时判成 supported） |
| 10 | `_api.py:880` | 「it cannot stop another process or the filesystem from removing the pathname」 | 未命中（@9 时判成 supported） |
| 11 | `_api.py:873` | 「It has no effect on Windows or SoftFileLock」 | 未命中（@9 时判成 supported） |
| 12 | `_strict.py:171` | 「a strict claim is never broken by age, only by force_break()」 | 未命中（@9 时判成 supported） |
| 13 | `_soft.py:532` | 「Windows cannot unlink an open file, so the unlink outlives the hold」 | 未命中（**仍判成 supported**） |
| 14 | `base.py:244-245` | 「Cannot send to a coroutine function.」 | 未命中 |
| 15 | `base.py:293-295` | 「Cannot send to a non-coroutine function.」 | 未命中 |
| 16 | `base.py:60-63` | 「This signal cannot be emitted by an automatic disconnect」 | 未命中 |
| 17 | `base.py:308-310` | 「Does not check if weakly referenced receivers are still live」 | 未命中（@9 时判成 supported） |
| 18 | `base.py:445` | 「with the caveat that such pruning is not threadsafe」 | 未命中 |
| 19 | `signer.py:147-152` | sep 落在 base64 alphabet 内则抛 `ValueError` | 未命中 |
| 20 | `url_safe.py:45-52` | zlib 解压失败抛 `BadPayload` | 未命中 |
| 21 | `signer.py:22` | `SigningAlgorithm.get_signature` 直接 `raise NotImplementedError()` | 未命中（**仍判成 supported**） |
| 22 | `signer.py:213` | `raise TypeError("Unknown key derivation method")` | 未命中（**仍判成 supported**） |
| 23 | `signer.py:32-36` | 「an algorithm that does not perform any signing and returns an empty signature」 | 未命中 |
| 24 | `timed.py:106` | `raise BadTimeSignature("timestamp missing", …)` | 未命中（@9 时判成 supported） |
| 25 | `timed.py:135` | `raise BadTimeSignature("Malformed timestamp", …)` | 未命中（@9 时判成 supported） |
| 26 | `url_safe.py:37-42` | 「Could not base64 decode the payload」→ `BadPayload` | 未命中 |
| 27 | `serializer.py:263-265` | 「Could not load the payload …」→ `BadPayload` | 未命中 |
| 28 | `signer.py:249` | `raise BadSignature(f"No {self.sep!r} found in value")` | 未命中（@9 时判成 supported） |
| 29 | `markupsafe/__init__.py:335-337` | `raise ValueError("Unsupported format specification for Markup.")` | 未命中（@9 时判成 supported） |
| 30 | `markupsafe/__init__.py:352-356` | 「does not define __html_format__. A class that defines __html__ must define __html_format__」 | 未命中（@9 时判成 supported） |

## 统计（v5，30 条）

| 指标 | 数值 | 计算 |
|---|---|---|
| 反证召回（结论判对为 contradicted） | **3.3%** | 1/30 |
| 反证定位准确 | **100%** | 1/1（唯一一条反证的定位就是真证据行） |
| 反向错误（真 contradicted 判成 supported） | **20.0%** | 6/30 |
| 漏报（真 contradicted 判成 no_evidence） | **76.7%** | 23/30 |

分库：

| 库 | 条数 | contradicted | supported（反向错误） | no_evidence（漏报） |
|---|---|---|---|---|
| filelock | 13 | 1 | 4 | 8 |
| blinker | 5 | 0 | 0 | 5 |
| itsdangerous | 10 | 0 | 2 | 8 |
| markupsafe | 2 | 0 | 0 | 2 |
| **合计** | **30** | **1** | **6** | **23** |

列校验：1 + 6 + 23 = 30；分库 13 + 5 + 10 + 2 = 30，各项分库合计与总计一致。
三态之外无判定域外条目、无不可验收条目（四份报告「需求可判定性预检」均为「N 条可判定，0 条无法验收」）。

## 版本对照：@9 → @10（引用这些数字时必须带版本号）

同一批 30 条样本、同一批需求清单，两版判据的实测结果：

| 判据版本 | 产物 | contradicted | supported（反向错误） | no_evidence（漏报） | 召回 | 反向错误率 | 漏报率 |
|---|---|---|---|---|---|---|---|
| `C-MATCHER@9` | `.tmp/label/spec-neg-*-v4.md` | 1 | 18 | 11 | 1/30 = 3.3% | **18/30 = 60.0%** | 11/30 = 36.7% |
| **`C-MATCHER@10`（当前）** | 本目录 `spec-neg-*-v5.md` | **1** | **6** | **23** | 1/30 = 3.3% | **6/30 = 20.0%** | **23/30 = 76.7%** |

分库对照（contradicted / supported / no_evidence）：

| 库 | 条数 | @9 | @10 |
|---|---|---|---|
| filelock | 13 | 1 / 10 / 2 | **1 / 4 / 8** |
| blinker | 5 | 0 / 1 / 4 | **0 / 0 / 5** |
| itsdangerous | 10 | 0 / 5 / 5 | **0 / 2 / 8** |
| markupsafe | 2 | 0 / 2 / 0 | **0 / 0 / 2** |
| **合计** | **30** | **1 / 18 / 11** | **1 / 6 / 23** |

**反向错误 18/30 = 60.0% → 6/30 = 20.0%，同一批样本、同一批声称，只因判据版本不同就相差 40 个百分点。**
因此这个指标**对判据版本极度敏感**，引用时必须带版本号（`C-MATCHER@10`），
不得把它当作引擎的固定能力值，也不得与 `anchor-neg-10.md` 里 @9 的 20%（2/10）跨版本混算——
两个 20% 只是数值巧合，分母（30 vs 10）与判据版本都不同。

同一 10 条子集在 @10 产物中的复算（filelock #1-5、blinker #1-3、itsdangerous #1-2，
即 `anchor-neg-10.md` 的样本）：contradicted 1 / supported **0** / no_evidence 9，
反向错误 **0/10 = 0%**、召回 1/10 = 10%、漏报 9/10 = 90%。
`anchor-neg-10.md` 保留 @9 的原样记录（反向错误 2/10 = 20%）作历史对照，两处数字版本不同、不可互换。

## 机制：@10 把 12 条 supported 打回 no_evidence 的原因

`C-MATCHER@10`（原文见 `gap-engine/contract/CONTRACT.md` 的同名小节）新增「正证据最低形态与参数覆盖」：
`^import` / `from … import` 行、`tests/` 下文件、未提及声称参数的 `def` 行都不再算有效正证据，
声称里出现显式 `k=v` 或实现词组时证据行还必须命中全部参数组。@9 判 supported 的 18 条里 12 条被打回：

| @9 定位（取自 `spec-neg-*-v4.md`） | 该行内容 | 打回条数 | 条目 |
|---|---|---|---|
| `tests/test_soft_lifetime_warning.py:204` | `def test_soft_lifetime_warning_shows_under_default_filters(tmp_path: Path) -> None:` | 2 | #2、#12 |
| `tests/test_leak.py:11` | `def test_markup_leaks() -> None:` | 2 | #29、#30 |
| `src/filelock/_descriptor.py:37` | `def lock_descriptor(fd: int, *, blocking: bool = True, …) -> bool:` | 3 | #3、#9、#10 |
| `src/filelock/_windows.py:104` | `class _UNICODE_STRING(ctypes.Structure):` | 1 | #11 |
| `src/blinker/base.py:24` | `class Signal:` | 1 | #17 |
| `src/itsdangerous/timed.py:22` | `class TimestampSigner(Signer):` | 2 | #24、#25 |
| `src/itsdangerous/signer.py:15` | `class SigningAlgorithm:` | 1 | #28 |
| **合计** | — | **12** | — |

仍判 supported 的 6 条，逐条看它们为什么没被过滤：

| 条目 | @10 定位 | 该行内容 | 漏过滤的原因 |
|---|---|---|---|
| #6、#7 | `tasks/benchmark.py:4` | 注释行（`latency, the way … describes. Run with …`） | `_is_test_file` 只认 `/tests/`、`/test_`、`test_` 前缀，`tasks/benchmark.py` 不属于测试文件 |
| #8 | `src/filelock/_read_write.py:62` | `register_fork_class as _register_fork_class,` | 多行 `from … import (` 的**续行**，不匹配以 `import` 开头的 `_IMPORT_LINE_RE` |
| #13 | `src/filelock/_marker.py:53` | `class MarkerSoftFileLock(SoftFileLock):` | 弱形态表只列了 `def` 行，`class` 声明行不在其中 |
| #21、#22 | `src/itsdangerous/signer.py:15` | `class SigningAlgorithm:` | 同上；真否定在 `signer.py:22`、`signer.py:213`，同一文件内被漏掉 |

结论：@10 把「凡声称里出现实现中存在的标识符就报 supported」的比例从 18/30 压到 6/30，
残留 6 条集中在三处过滤缺口——`class` 声明行未列入弱形态、多行 import 的续行未匹配、
`tasks/` 这类非 `tests/` 的脚本目录未被识别；**参数级适用范围判断仍未解决**。

## 备注

- `anchor-neg-10.md` 的 10 条原样保留（@9 记录），编号 1-10 与本文件一致，可直接对照；本文件编号 1-30 沿用 v4 扩样版，未变动。
- 报告产物：`spec-neg-{filelock,blinker,itsdangerous,markupsafe}-v5.md`（本目录，`C-MATCHER@10`）；@9 产物留在 `.tmp/label/spec-neg-*-v4.md`，不入库。
- 本轮只运行引擎与重算统计，未改动 gap-engine 任何源码、契约、测试与 `reports/`。
- 复算脚本：`.tmp/diag/recompute_at10.py`（输出 `.tmp/diag/recompute_at10.json`，逐条含结论与 `locator`）。
