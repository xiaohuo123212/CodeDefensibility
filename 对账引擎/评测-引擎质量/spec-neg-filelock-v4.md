# filelock 需求对账报告

这是 spec 模式：报告只说明我查过哪里，不说明你没做过。

## 需求可判定性预检

共 13 条需求，13 条可判定，0 条无法验收。

## 项目实际是什么

- 文件 110 个，代码 9883 行
- 入口：未识别到启动入口
- 依赖：cachetools==7.2.7 \, colorama==0.4.6 \, distlib==0.4.4 \, filelock==4.2.4 \, packaging==26.3 \
- 测试：40 个测试文件
- 一句话：未识别到启动入口；依赖 12 个（cachetools==7.2.7 \, colorama==0.4.6 \）；40 个测试文件。

## 概览

#### 查过 4754 处（13 条需求，9 类探测项）

- 其中不同位置 737 处（同一探测项被多条需求重复扫描时只计一次）

- 有证据 10 条 / 没找到证据 2 条 / 有反证 1 条

## 逐条

### AsyncFileLock 支持用同步 with 语句加锁

来源：req-neg-filelock.md#L6

查到：

- 相关实现：1 处
  - tests/test_async_filelock_transition_admission.py:31

查过没找到：

- 路由/入口：0 处（扫过 88 处）
- 依赖声明：0 处（扫过 2 处）
- 测试覆盖：0 处（扫过 52 处）
- 否定/未实现声明：0 处（扫过 110 处）

结论：代码里有反证，与要求不一致

- 定位：src/filelock/asyncio.py:317

会被问：「AsyncFileLock 支持用同步 with 语句加锁」的要求与代码里的否定声明冲突，最终以哪边为准？

该补什么：代码与要求不一致：先确认这条要求是否仍然有效；有效就改实现，无效就改需求文档，不要两边都留着。

audit effort：5 类 340 处

### FileLock 支持用 lifetime 参数按文件年龄强制过期

来源：req-neg-filelock.md#L7

查到：

- 路由/入口：1 处
  - tests/test_soft_lifetime_warning.py:204
- 依赖声明：1 处
  - tasks/termux/requirements.txt:15
- 相关实现：11 处
  - tests/async_filelock_cancellation_helpers.py:15
  - tests/test_async_filelock.py:57
  - tests/test_async_filelock_acquire_cancellation.py:28
  - tests/test_async_filelock_release_cancellation.py:28
  - tests/test_async_filelock_rollback_agnostic.py:17
- 否定/未实现声明：4 处
  - tests/test_filelock.py:1022
  - tests/test_filelock.py:1496
  - tests/test_filelock.py:1499
  - tests/test_filelock.py:4213

查过没找到：

- 测试覆盖：0 处（扫过 52 处）

结论：有证据

会被问：「FileLock 支持用 lifetime 参数按文件年龄强制过期」对应的入口/路由与实现文件分别在哪里？能否给出一条可复现的调用？

该补什么：无需补齐：证据已足够。

audit effort：5 类 340 处

### SoftFileLock 支持 preserve_lock_file=True 保留锁文件不删

来源：req-neg-filelock.md#L8

查到：

- 相关实现：3 处
  - src/filelock/_descriptor.py:37
  - src/filelock/_marker.py:53
  - src/filelock/_soft.py:82
- 否定/未实现声明：1 处
  - tests/test_util.py:613

查过没找到：

- 路由/入口：0 处（扫过 88 处）
- 依赖声明：0 处（扫过 2 处）
- 测试覆盖：0 处（扫过 52 处）

结论：有证据

会被问：「SoftFileLock 支持 preserve_lock_file=True…」对应的入口/路由与实现文件分别在哪里？能否给出一条可复现的调用？

该补什么：无需补齐：证据已足够。

audit effort：5 类 340 处

### 所有锁类型都支持 on_acquired 回调拿到文件描述符

来源：req-neg-filelock.md#L9

查到：

- （无）

查过没找到：

- 路由/入口：0 处（扫过 88 处）
- 依赖声明：0 处（扫过 2 处）
- 相关实现：0 处（扫过 88 处）
- 测试覆盖：0 处（扫过 52 处）
- 否定/未实现声明：0 处（扫过 110 处）

结论：没找到证据（该补）

会被问：「所有锁类型都支持 on_acquired 回调拿到文件描述符」对应的入口/路由与实现文件分别在哪里？能否给出一条可复现的调用？

该补什么：在 README 里给出该功能的入口定义与实现文件相对路径。

audit effort：5 类 340 处

### 同一个锁类允许用不同参数创建多个单例实例

来源：req-neg-filelock.md#L10

查到：

- （无）

查过没找到：

- 路由/入口：0 处（扫过 88 处）
- 依赖声明：0 处（扫过 2 处）
- 相关实现：0 处（扫过 88 处）
- 测试覆盖：0 处（扫过 52 处）
- 否定/未实现声明：0 处（扫过 110 处）

结论：没找到证据（该补）

会被问：「同一个锁类允许用不同参数创建多个单例实例」对应的入口/路由与实现文件分别在哪里？能否给出一条可复现的调用？

该补什么：在 README 里给出该功能的入口定义与实现文件相对路径。

audit effort：5 类 340 处

### AsyncFileLock 在 thread_local=True 时仍支持 run_in_executor=True

来源：req-neg-filelock.md#L11

查到：

- 压测脚本：2 处
  - tasks/benchmark.py:4
  - tox.toml:177
- 并发原语：40 处
  - src/filelock/_api.py:801
  - src/filelock/_async.py:68
  - src/filelock/_async.py:64
  - src/filelock/_async_read_write.py:28
  - src/filelock/_async_read_write.py:155
- worker 配置：14 处
  - src/filelock/_async_read_write.py:132
  - tests/soft_rw/test_soft_rw_async.py:204
  - tests/soft_rw/test_soft_rw_sync.py:320
  - tests/test_async_filelock.py:245
  - tests/test_async_filelock_acquire_cancellation.py:157
- 连接池：4 处
  - tests/soft_rw/test_soft_rw_sync.py:320
  - tests/test_filelock.py:755
  - tests/test_fork_coordination.py:1427
  - tests/test_fork_registries.py:116
- 否定/未实现声明：13 处
  - src/filelock/_strict.py:830
  - src/filelock/asyncio.py:317
  - src/filelock/asyncio.py:327
  - tasks/verify_filesystem.py:21
  - tests/test_filelock.py:1022

查过没找到：

- （无）

结论：有证据

会被问：「AsyncFileLock 在 thread_local=True 时仍支持 …」是在哪份压测脚本和哪种进程/线程配置下测得的？结果文件在哪里？

该补什么：无需补齐：证据已足够。

audit effort：5 类 507 处

### SoftFileLock 支持非默认的锁选项（如 thread_local=True）

来源：req-neg-filelock.md#L12

查到：

- 压测脚本：2 处
  - tasks/benchmark.py:4
  - tox.toml:177
- 并发原语：40 处
  - src/filelock/_api.py:801
  - src/filelock/_async.py:68
  - src/filelock/_async.py:64
  - src/filelock/_async_read_write.py:28
  - src/filelock/_async_read_write.py:155
- worker 配置：14 处
  - src/filelock/_async_read_write.py:132
  - tests/soft_rw/test_soft_rw_async.py:204
  - tests/soft_rw/test_soft_rw_sync.py:320
  - tests/test_async_filelock.py:245
  - tests/test_async_filelock_acquire_cancellation.py:157
- 连接池：4 处
  - tests/soft_rw/test_soft_rw_sync.py:320
  - tests/test_filelock.py:755
  - tests/test_fork_coordination.py:1427
  - tests/test_fork_registries.py:116
- 否定/未实现声明：13 处
  - src/filelock/_strict.py:830
  - src/filelock/asyncio.py:317
  - src/filelock/asyncio.py:327
  - tasks/verify_filesystem.py:21
  - tests/test_filelock.py:1022

查过没找到：

- （无）

结论：有证据

会被问：「SoftFileLock 支持非默认的锁选项（如 thread_local=T…」是在哪份压测脚本和哪种进程/线程配置下测得的？结果文件在哪里？

该补什么：无需补齐：证据已足够。

audit effort：5 类 507 处

### FileLock 在 fork 出的子进程里可以直接复用父进程构造的实例

来源：req-neg-filelock.md#L13

查到：

- 路由/入口：1 处
  - tests/test_fork_coordination.py:314
- 依赖声明：1 处
  - tasks/termux/requirements.txt:15
- 相关实现：17 处
  - src/filelock/_read_write.py:62
  - src/filelock/_soft_rw/_sync.py:54
  - tests/async_filelock_cancellation_helpers.py:15
  - tests/fork_helpers.py:13
  - tests/test_async_filelock.py:57
- 否定/未实现声明：4 处
  - tests/test_filelock.py:1022
  - tests/test_filelock.py:1496
  - tests/test_filelock.py:1499
  - tests/test_filelock.py:4213

查过没找到：

- 测试覆盖：0 处（扫过 52 处）

结论：有证据

会被问：「FileLock 在 fork 出的子进程里可以直接复用父进程构造的实例」对应的入口/路由与实现文件分别在哪里？能否给出一条可复现的调用？

该补什么：无需补齐：证据已足够。

audit effort：5 类 340 处

### ReadWriteLock 单例允许用不同的 timeout 和 blocking 复用同一实例

来源：req-neg-filelock.md#L14

查到：

- 相关实现：3 处
  - src/filelock/_descriptor.py:37
  - src/filelock/_error.py:8
  - tests/test_error.py:24

查过没找到：

- 路由/入口：0 处（扫过 88 处）
- 依赖声明：0 处（扫过 2 处）
- 测试覆盖：0 处（扫过 52 处）
- 否定/未实现声明：0 处（扫过 110 处）

结论：有证据

会被问：「ReadWriteLock 单例允许用不同的 timeout 和 blocki…」对应的入口/路由与实现文件分别在哪里？能否给出一条可复现的调用？

该补什么：无需补齐：证据已足够。

audit effort：5 类 340 处

### preserve_lock_file=True 能阻止其它进程删除锁文件路径

来源：req-neg-filelock.md#L15

查到：

- 相关实现：1 处
  - src/filelock/_descriptor.py:37
- 否定/未实现声明：1 处
  - tests/test_util.py:613

查过没找到：

- 路由/入口：0 处（扫过 88 处）
- 依赖声明：0 处（扫过 2 处）
- 测试覆盖：0 处（扫过 52 处）

结论：有证据

会被问：「preserve_lock_file=True 能阻止其它进程删除锁文件路径」对应的入口/路由与实现文件分别在哪里？能否给出一条可复现的调用？

该补什么：无需补齐：证据已足够。

audit effort：5 类 340 处

### fallback_to_soft 参数在 Windows 平台上同样生效

来源：req-neg-filelock.md#L16

查到：

- 相关实现：2 处
  - src/filelock/_windows.py:104
  - tests/test_read_write.py:37

查过没找到：

- 路由/入口：0 处（扫过 88 处）
- 依赖声明：0 处（扫过 2 处）
- 测试覆盖：0 处（扫过 52 处）
- 否定/未实现声明：0 处（扫过 110 处）

结论：有证据

会被问：「fallback_to_soft 参数在 Windows 平台上同样生效」对应的入口/路由与实现文件分别在哪里？能否给出一条可复现的调用？

该补什么：无需补齐：证据已足够。

audit effort：5 类 340 处

### StrictSoftFileLock 的 lifetime 参数能按文件年龄清除陈旧声明

来源：req-neg-filelock.md#L17

查到：

- 路由/入口：1 处
  - tests/test_soft_lifetime_warning.py:204
- 相关实现：2 处
  - tests/test_lifetime_validation.py:55
  - tests/test_soft_lifetime_warning.py:33

查过没找到：

- 依赖声明：0 处（扫过 2 处）
- 测试覆盖：0 处（扫过 52 处）
- 否定/未实现声明：0 处（扫过 110 处）

结论：有证据

会被问：「StrictSoftFileLock 的 lifetime 参数能按文件年龄清…」对应的入口/路由与实现文件分别在哪里？能否给出一条可复现的调用？

该补什么：无需补齐：证据已足够。

audit effort：5 类 340 处

### SoftFileLock 在 Windows 上释放时会立即删除锁文件

来源：req-neg-filelock.md#L18

查到：

- 相关实现：4 处
  - src/filelock/_marker.py:53
  - src/filelock/_soft.py:82
  - src/filelock/_windows.py:104
  - tests/test_read_write.py:37

查过没找到：

- 路由/入口：0 处（扫过 88 处）
- 依赖声明：0 处（扫过 2 处）
- 测试覆盖：0 处（扫过 52 处）
- 否定/未实现声明：0 处（扫过 110 处）

结论：有证据

会被问：「SoftFileLock 在 Windows 上释放时会立即删除锁文件」对应的入口/路由与实现文件分别在哪里？能否给出一条可复现的调用？

该补什么：无需补齐：证据已足够。

audit effort：5 类 340 处

## 未覆盖

- 无

## 局限

- 本批只跑单轮检索，多轮换假设未启用。
- 只把显式否定声明当反证：没有显式否定时不下断言。
- 缺口判定依赖先验普遍性表（PREVALENCE），尚未用同类项目实测。
- 规则优先，LLM 默认关闭；分类歧义未做消解。
- 报告只反映我查过的位置，不等于你没做过。
- spec 模式的补齐物生成与多轮换假设尚未启用。
