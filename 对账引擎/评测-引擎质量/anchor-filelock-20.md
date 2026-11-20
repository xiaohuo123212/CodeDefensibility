# filelock 20 条声称的标注结果（`C-MATCHER@10` 复算）

真值判定方式：逐条到代码里找实现证据，不看文档自述。
需求来源：`filelock/docs/index.rst`「Lock Types」与「Platform Support」。
标注结论：**20 条全部有真实实现**，真值均为 `supported`。
当前引擎报告：`spec-filelock-20-v6.md`（`C-MATCHER@10` 产物，本目录内）。

下表的 `v1` / `v3` / `v5` 列只作历史对照（分别为 `@7`、`@8`、`@9` 产物），`v6` 列是当前结论。
符号：`有证据` = supported、`没找到` = no_evidence、`有反证` = contradicted。

| # | 声称 | v1 | v3 | v5 | v6（@10） | 真值 | v6 判定 | 代码证据 |
|---|---|---|---|---|---|---|---|---|
| 1 | 提供平台无关的文件锁 | 没找到 | 没找到 | 没找到 | 没找到 | supported | 漏报 | `_unix.py`（flock）、`_windows.py`（LockFileEx）双后端 |
| 2 | 提供进程间同步 | 没找到 | 没找到 | 没找到 | 没找到 | supported | 漏报 | 同上，锁对象以文件路径为身份 |
| 3 | FileLock 自动选原生后端，否则回退软标记 | 有反证 | 有反证 | 有证据 | **有证据** | supported | 正确 | `_unix.py:224` 回退逻辑即实现本身 |
| 4 | 支持可取消的 acquire | 有证据 | 有证据 | 有证据 | **没找到** | supported | 漏报（@10 降级） | `_api.py` acquire 支持 cancel |
| 5 | 支持自死锁检测 | 没找到 | 没找到 | 没找到 | 没找到 | supported | 漏报 | `_api.py:423-427,722,766` deadlock-registry |
| 6 | SoftFileLock 不需要原生锁 API | 有反证 | 有证据 | 有证据 | **有证据** | supported | 正确 | `_soft.py`、`_marker.py` 纯文件标记 |
| 7 | SoftFileLock 支持同主机 PID 检查 | 有反证 | 有证据 | 有证据 | **有证据** | supported | 正确 | `_identity.py:25`、`_soft.py:82` |
| 8 | SoftFileLock 通过进程启动标识回收持有者 | 有反证 | 有证据 | 有证据 | **有证据** | supported | 正确 | `_identity.py` 进程启动标识 |
| 9 | StrictSoftFileLock 从不猜测持有者已死 | 没找到 | 没找到 | 没找到 | 没找到 | supported | 漏报 | `_strict.py:163` 类定义与 fail-closed 语义 |
| 10 | StrictSoftFileLock 按唯一名称移除声明 | 没找到 | 没找到 | 没找到 | 没找到 | supported | 漏报 | `_strict.py` 唯一名机制 |
| 11 | SoftFileLease 提供带心跳的过期声明 | 有证据 | 有证据 | 有证据 | **没找到** | supported | 漏报（@10 降级） | `_lease.py:67,107,116` heartbeat |
| 12 | SoftFileLease 支持 on_compromise 回调 | 有证据 | 有证据 | 有证据 | **没找到** | supported | 漏报（@10 降级） | `_lease.py:84` |
| 13 | ReadWriteLock 并发读者 + 单写者 | 有证据 | 有证据 | 有证据 | **有证据** | supported | 正确 | `_read_write.py` SQLite 后端 |
| 14 | ReadWriteLock 默认单例 | 没找到 | 没找到 | 没找到 | 没找到 | supported | 漏报 | `_read_write.py:458-464` `_instances` WeakValueDictionary |
| 15 | ReadWriteLock 按模式重入 | 没找到 | 没找到 | 没找到 | 没找到 | supported | 漏报 | `_read_write.py:431-448` `read_depths` |
| 16 | SoftReadWriteLock 写者优先 | 没找到 | 没找到 | 没找到 | 没找到 | supported | 漏报 | `_read_write.py:699` writer preference |
| 17 | SoftReadWriteLock 无时钟心跳过期 | 没找到 | 没找到 | 没找到 | 没找到 | supported | 漏报 | `_soft_rw.py` generation log |
| 18 | AsyncFileLock 支持 async/await | 有反证 | 有证据 | 有证据 | **有证据** | supported | 正确 | `asyncio.py` 全套异步锁 |
| 19 | AsyncFileLock 自定义 executor 与事件循环 | 有反证 | 有证据 | 有证据 | **没找到** | supported | 漏报（@10 降级） | `asyncio.py:166-174` executor 参数 |
| 20 | Windows 后端用 LockFileEx 加锁 | 有反证 | 有证据 | 有证据 | **有证据** | supported | 正确 | `_windows.py:104` |

## 统计（当前 `@10` + 历史对照）

| 版本 | 有证据 | 没找到证据 | 有反证 | 判对 | 漏报 | 误报 |
|---|---|---|---|---|---|---|
| v1（C-EXTRACTOR@7） | 4 | 9 | 7 | 20.0% | 45.0% | 35.0% |
| v2（@8 前四类） | 8 | 9 | 3 | 40.0% | 45.0% | 15.0% |
| v3（@8 六类） | 10 | 9 | 1 | 50.0% | 45.0% | 5.0% |
| v5（@9，`spec-filelock-20-v5.md`） | 11 | 9 | 0 | 55.0% | 45.0% | 0% |
| **v6（@10，`spec-filelock-20-v6.md`）** | **7** | **13** | **0** | **7/20 = 35.0%** | **13/20 = 65.0%** | **0/20 = 0%** |

列校验：7 + 13 + 0 = 20；判对 7 + 漏报 13 + 误报 0 = 20。

口径定义：判对 =「引擎给出的确定结论且与真值一致」/ 总数；漏报 = 真 supported 判成 `no_evidence`；误报 = 真 supported 判成 `contradicted`。

二分类（把「有证据」与「有反证」都算作引擎下了确定判断）：

| 版本 | precision | recall |
|---|---|---|
| v1 | 4/11 = 36.4% | 4/20 = 20.0% |
| v3 | 10/11 = 90.9% | 10/20 = 50.0% |
| v5 | 11/11 = 100% | 11/20 = 55.0% |
| **v6（当前）** | **7/7 = 100%** | **7/20 = 35.0%** |

计算过程：precision = 判对数 /（有证据数 + 有反证数）；recall = 判对数 / 真 supported 数（本样本 20 条真值全为 supported，故分母恒为 20）。

反证专项准确率：样本内真 `contradicted` 为 0 条；v3 时报出 1 条（**0/1**），**v5 起报出 0 条 → 不适用**。该样本无法衡量反证能力，见「样本偏置说明」。

## @10 降级的 4 条（v5 有证据 → v6 没找到证据）

`C-MATCHER@10` 要求正证据不是 `import` 行、不是 `tests/` 文件、不是未提及声称参数的 `def` 签名。这 4 条在 @9 时的证据都属于上述形态：

| # | 声称 | @9 定位（`spec-filelock-20-v5.md`） | 该行内容 | 降级原因 |
|---|---|---|---|---|
| 4 | 支持可取消的 acquire | `tests/test_async_filelock_acquire_cancellation.py:28` | 测试中的同名调用 | 证据全在 `tests/`，测试调用不证明实现支持该参数组合 |
| 11 | SoftFileLease 提供带心跳的过期声明 | `src/filelock/_lease.py:62` | `class SoftFileLease(MarkerSoftFileLock):` | 类声明行只证明类存在与基类 |
| 12 | SoftFileLease 支持 on_compromise 回调 | `src/filelock/_lease.py:62` | 同上 | 同上 |
| 19 | AsyncFileLock 自定义 executor 与事件循环 | `tests/test_async_filelock_runner_shutdown.py:23` | 测试中的同名调用 | 证据全在 `tests/` |

这 4 条的真值仍是 `supported`（代码证据列已逐条给出），所以它们计入「漏报」，不计入「误报」。
四条之外另有 9 条（#1、#2、#5、#9、#10、#14、#15、#16、#17）在 v1→v6 五版里恒为「没找到证据」。

## 已修的 6 条误报（@8 否定作用域）

否定抽取器改前只看字面「not supported / unsupported」，不判断否定落在什么语境。按 `C-EXTRACTOR@8` 六类作用域整改后，6 条误报转为正确：

| 被当成反证的位置 | 实际语义 | @8 拦下的规则 |
|---|---|---|
| `_api.py:524` | `lifetime` 参数对该锁类型无效的参数校验警告 | 参数校验型异常 / 待抛消息 |
| `_api.py:613`、`:614`、`:626` | `if preserve and not supported:` 布尔取反 + `msg = f"... is not supported ..."` | 控制流取反 + 待抛消息赋值 |
| `_unix.py:224` | 「flock 在此文件系统不可用，回退到 SoftFileLock」——本身就是第 3 条的实现 | 回退/降级说明 |
| `_strict.py:154` | 注释里引用的 errno 英文短语 `"operation not supported"` | 注释内引号英文短语 |
| `_strict.py:1213`、`:1217` | `_HARD_LINK_UNSUPPORTED_ERRNOS` 标识符 | 标识符内否定词 |
| `asyncio.py:170` | `thread_local=True` 与 `run_in_executor` 的非法参数组合 | 待抛消息赋值 |
| `test_async_filelock.py:376` | 测试中 `pytest.raises(match=...)` 的期望异常文本 | 测试期望 |

## 第 3 条误报：已由 `C-MATCHER@8/@9` 清零

v3 把第 3 条判成 `contradicted`，其否定证据与修法如下：

| 位置 | 内容性质 | 哪一版修掉 |
|---|---|---|
| `_strict.py:830` | 「Termux 无 `os.link`，报为 unsupported」——讲硬链接平台条件，与「原生后端回退」无关；**因路径 `src/filelock/` 含 `filelock` 而被判相关** | `@9` 路径只认文件名 |
| `asyncio.py:317`、`:327` | docstring 真的写着「Sync context manager entry is not supported」——真否定声明，不应屏蔽 | 与本条仍不相关（相关性由 Matcher 判） |
| `test_filelock.py:1022` | `pytest.mark.filterwarnings("ignore:flock not supported ...")` | `@8` 测试期望守卫 |
| `test_filelock.py:1496` | `# ty: ignore[unsupported-base]` | `@8` 注释 pragma 守卫 |

v5 与 v6 该条均为「有证据」，有反证 0 条，误报未复现。**残留问题**：v6 该条「相关实现」首项仍是 `tests/async_filelock_cancellation_helpers.py:15`，证据质量待改善（同类问题见 `anchor-neg-30.md` 的 @10 残留 6 条）。

## 13 条漏报的共同根因（本轮未修）

声称表述偏抽象时，探测关键词匹配不到实现：
- 「平台无关」「进程间同步」→ 实现散在 `_unix.py` / `_windows.py`，不含这些词
- 「单例」「重入」「写者优先」「无时钟」→ 实现是 `_instances` / `read_depths` / `writer preference`，用词不同
- 「自死锁检测」→ 实现叫 `deadlock-registry`
- @10 新增的 4 条（#4、#11、#12、#19）不属于词表问题：它们的证据在 @9 时确实被找到了，是**证据形态不合格**（`tests/` 文件、类声明行）被 @10 的弱形态过滤挡回。

## 样本偏置说明

这批 20 条全部取自作者自己文档的特性自述，真值天然全是 supported。因此本评测只能衡量「能不能找到证据」，**测不到「能不能识别未实现」**。真实需求清单里通常混有大量未实现项，届时漏报率会好看很多，误报率不受影响。反证能力另由 `anchor-neg-30.md` 的 30 条反向构造样本衡量（`C-MATCHER@10`：召回 1/30 = 3.3%、定位 1/1 = 100%、反向错误 6/30 = 20.0%、漏报 23/30 = 76.7%）。