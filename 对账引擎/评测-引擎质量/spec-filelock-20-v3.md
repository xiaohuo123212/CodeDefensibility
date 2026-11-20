# filelock 需求对账报告

这是 spec 模式：报告只说明我查过哪里，不说明你没做过。

## 需求可判定性预检

共 20 条需求，20 条可判定，0 条无法验收。

## 项目实际是什么

- 文件 110 个，代码 9883 行
- 入口：未识别到启动入口
- 依赖：cachetools==7.2.7 \, colorama==0.4.6 \, distlib==0.4.4 \, filelock==4.2.4 \, packaging==26.3 \
- 测试：40 个测试文件
- 一句话：未识别到启动入口；依赖 12 个（cachetools==7.2.7 \, colorama==0.4.6 \）；40 个测试文件。

## 概览

#### 查过 7134 处（20 条需求，9 类探测项）

- 其中不同位置 737 处（同一探测项被多条需求重复扫描时只计一次）

- 有证据 10 条 / 没找到证据 9 条 / 有反证 1 条

## 逐条

### 提供平台无关的文件锁

来源：req-filelock-20.md#L3

查到：

- （无）

查过没找到：

- 路由/入口：0 处（扫过 88 处）
- 依赖声明：0 处（扫过 2 处）
- 相关实现：0 处（扫过 88 处）
- 测试覆盖：0 处（扫过 52 处）
- 否定/未实现声明：0 处（扫过 110 处）

结论：没找到证据（该补）

会被问：「提供平台无关的文件锁」对应的入口/路由与实现文件分别在哪里？能否给出一条可复现的调用？

该补什么：在 README 里给出该功能的入口定义与实现文件相对路径。

audit effort：5 类 340 处

### 提供进程间同步

来源：req-filelock-20.md#L4

查到：

- （无）

查过没找到：

- 路由/入口：0 处（扫过 88 处）
- 依赖声明：0 处（扫过 2 处）
- 相关实现：0 处（扫过 88 处）
- 测试覆盖：0 处（扫过 52 处）
- 否定/未实现声明：0 处（扫过 110 处）

结论：没找到证据（该补）

会被问：「提供进程间同步」对应的入口/路由与实现文件分别在哪里？能否给出一条可复现的调用？

该补什么：在 README 里给出该功能的入口定义与实现文件相对路径。

audit effort：5 类 340 处

### FileLock 在可用时自动选择原生后端，否则回退到软标记

来源：req-filelock-20.md#L5

查到：

- 路由/入口：1 处
  - src/filelock/_error.py:51
- 依赖声明：1 处
  - tasks/termux/requirements.txt:15
- 相关实现：29 处
  - src/filelock/__init__.py:159
  - src/filelock/_api.py:79
  - src/filelock/_async.py:58
  - src/filelock/_async_read_write.py:84
  - src/filelock/_descriptor.py:37
- 否定/未实现声明：7 处
  - src/filelock/_strict.py:830
  - src/filelock/asyncio.py:317
  - src/filelock/asyncio.py:327
  - tests/test_filelock.py:1022
  - tests/test_filelock.py:1496

查过没找到：

- 测试覆盖：0 处（扫过 52 处）

结论：代码里有反证，与要求不一致

- 定位：src/filelock/_strict.py:830

会被问：「FileLock 在可用时自动选择原生后端，否则回退到软标记」的要求与代码里的否定声明冲突，最终以哪边为准？

该补什么：代码与要求不一致：先确认这条要求是否仍然有效；有效就改实现，无效就改需求文档，不要两边都留着。

audit effort：5 类 340 处

### 支持可取消的 acquire

来源：req-filelock-20.md#L6

查到：

- 相关实现：4 处
  - tests/test_async_filelock_acquire_cancellation.py:28
  - tests/test_async_filelock_runner_shutdown.py:23
  - tests/test_async_filelock_transition_admission.py:31
  - tests/test_strict_soft.py:38

查过没找到：

- 路由/入口：0 处（扫过 88 处）
- 依赖声明：0 处（扫过 2 处）
- 测试覆盖：0 处（扫过 52 处）
- 否定/未实现声明：0 处（扫过 110 处）

结论：有证据

会被问：「支持可取消的 acquire」对应的入口/路由与实现文件分别在哪里？能否给出一条可复现的调用？

该补什么：无需补齐：证据已足够。

audit effort：5 类 340 处

### 支持自死锁检测

来源：req-filelock-20.md#L7

查到：

- （无）

查过没找到：

- 路由/入口：0 处（扫过 88 处）
- 依赖声明：0 处（扫过 2 处）
- 相关实现：0 处（扫过 88 处）
- 测试覆盖：0 处（扫过 52 处）
- 否定/未实现声明：0 处（扫过 110 处）

结论：没找到证据（该补）

会被问：「支持自死锁检测」对应的入口/路由与实现文件分别在哪里？能否给出一条可复现的调用？

该补什么：在 README 里给出该功能的入口定义与实现文件相对路径。

audit effort：5 类 340 处

### SoftFileLock 不需要原生锁 API

来源：req-filelock-20.md#L8

查到：

- 依赖声明：1 处
  - tasks/termux/requirements.txt:26
- 相关实现：3 处
  - src/filelock/_api.py:79
  - src/filelock/_marker.py:53
  - src/filelock/_soft.py:82

查过没找到：

- 路由/入口：0 处（扫过 88 处）
- 测试覆盖：0 处（扫过 52 处）
- 否定/未实现声明：0 处（扫过 110 处）

结论：有证据

会被问：「SoftFileLock 不需要原生锁 API」对应的入口/路由与实现文件分别在哪里？能否给出一条可复现的调用？

该补什么：无需补齐：证据已足够。

audit effort：5 类 340 处

### SoftFileLock 支持同主机 PID 检查

来源：req-filelock-20.md#L9

查到：

- 相关实现：4 处
  - src/filelock/_identity.py:25
  - src/filelock/_marker.py:53
  - src/filelock/_soft.py:82
  - tests/pid_namespace_helpers.py:16

查过没找到：

- 路由/入口：0 处（扫过 88 处）
- 依赖声明：0 处（扫过 2 处）
- 测试覆盖：0 处（扫过 52 处）
- 否定/未实现声明：0 处（扫过 110 处）

结论：有证据

会被问：「SoftFileLock 支持同主机 PID 检查」对应的入口/路由与实现文件分别在哪里？能否给出一条可复现的调用？

该补什么：无需补齐：证据已足够。

audit effort：5 类 340 处

### SoftFileLock 通过进程启动标识回收已消失的持有者

来源：req-filelock-20.md#L10

查到：

- 相关实现：2 处
  - src/filelock/_marker.py:53
  - src/filelock/_soft.py:82

查过没找到：

- 路由/入口：0 处（扫过 88 处）
- 依赖声明：0 处（扫过 2 处）
- 测试覆盖：0 处（扫过 52 处）
- 否定/未实现声明：0 处（扫过 110 处）

结论：有证据

会被问：「SoftFileLock 通过进程启动标识回收已消失的持有者」对应的入口/路由与实现文件分别在哪里？能否给出一条可复现的调用？

该补什么：无需补齐：证据已足够。

audit effort：5 类 340 处

### StrictSoftFileLock 从不猜测持有者已死

来源：req-filelock-20.md#L11

查到：

- （无）

查过没找到：

- 路由/入口：0 处（扫过 88 处）
- 依赖声明：0 处（扫过 2 处）
- 相关实现：0 处（扫过 88 处）
- 测试覆盖：0 处（扫过 52 处）
- 否定/未实现声明：0 处（扫过 110 处）

结论：没找到证据（该补）

会被问：「StrictSoftFileLock 从不猜测持有者已死」对应的入口/路由与实现文件分别在哪里？能否给出一条可复现的调用？

该补什么：在 README 里给出该功能的入口定义与实现文件相对路径。

audit effort：5 类 340 处

### StrictSoftFileLock 按唯一名称移除声明

来源：req-filelock-20.md#L12

查到：

- （无）

查过没找到：

- 路由/入口：0 处（扫过 88 处）
- 依赖声明：0 处（扫过 2 处）
- 相关实现：0 处（扫过 88 处）
- 测试覆盖：0 处（扫过 52 处）
- 否定/未实现声明：0 处（扫过 110 处）

结论：没找到证据（该补）

会被问：「StrictSoftFileLock 按唯一名称移除声明」对应的入口/路由与实现文件分别在哪里？能否给出一条可复现的调用？

该补什么：在 README 里给出该功能的入口定义与实现文件相对路径。

audit effort：5 类 340 处

### SoftFileLease 提供带心跳的过期声明

来源：req-filelock-20.md#L13

查到：

- 相关实现：1 处
  - src/filelock/_lease.py:62

查过没找到：

- 路由/入口：0 处（扫过 88 处）
- 依赖声明：0 处（扫过 2 处）
- 测试覆盖：0 处（扫过 52 处）
- 否定/未实现声明：0 处（扫过 110 处）

结论：有证据

会被问：「SoftFileLease 提供带心跳的过期声明」对应的入口/路由与实现文件分别在哪里？能否给出一条可复现的调用？

该补什么：无需补齐：证据已足够。

audit effort：5 类 340 处

### SoftFileLease 支持 on_compromise 回调

来源：req-filelock-20.md#L14

查到：

- 相关实现：1 处
  - src/filelock/_lease.py:62

查过没找到：

- 路由/入口：0 处（扫过 88 处）
- 依赖声明：0 处（扫过 2 处）
- 测试覆盖：0 处（扫过 52 处）
- 否定/未实现声明：0 处（扫过 110 处）

结论：有证据

会被问：「SoftFileLease 支持 on_compromise 回调」对应的入口/路由与实现文件分别在哪里？能否给出一条可复现的调用？

该补什么：无需补齐：证据已足够。

audit effort：5 类 340 处

### ReadWriteLock 支持并发读者与单一写者

来源：req-filelock-20.md#L15

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

会被问：「ReadWriteLock 支持并发读者与单一写者」是在哪份压测脚本和哪种进程/线程配置下测得的？结果文件在哪里？

该补什么：无需补齐：证据已足够。

- 判据：错误率 < 1% 且 P95 < 1s（行业惯例，需提出人确认）

audit effort：5 类 507 处

### ReadWriteLock 默认是单例

来源：req-filelock-20.md#L16

查到：

- （无）

查过没找到：

- 路由/入口：0 处（扫过 88 处）
- 依赖声明：0 处（扫过 2 处）
- 相关实现：0 处（扫过 88 处）
- 测试覆盖：0 处（扫过 52 处）
- 否定/未实现声明：0 处（扫过 110 处）

结论：没找到证据（该补）

会被问：「ReadWriteLock 默认是单例」对应的入口/路由与实现文件分别在哪里？能否给出一条可复现的调用？

该补什么：在 README 里给出该功能的入口定义与实现文件相对路径。

audit effort：5 类 340 处

### ReadWriteLock 支持按模式重入

来源：req-filelock-20.md#L17

查到：

- （无）

查过没找到：

- 路由/入口：0 处（扫过 88 处）
- 依赖声明：0 处（扫过 2 处）
- 相关实现：0 处（扫过 88 处）
- 测试覆盖：0 处（扫过 52 处）
- 否定/未实现声明：0 处（扫过 110 处）

结论：没找到证据（该补）

会被问：「ReadWriteLock 支持按模式重入」对应的入口/路由与实现文件分别在哪里？能否给出一条可复现的调用？

该补什么：在 README 里给出该功能的入口定义与实现文件相对路径。

audit effort：5 类 340 处

### SoftReadWriteLock 支持写者优先

来源：req-filelock-20.md#L18

查到：

- （无）

查过没找到：

- 路由/入口：0 处（扫过 88 处）
- 依赖声明：0 处（扫过 2 处）
- 相关实现：0 处（扫过 88 处）
- 测试覆盖：0 处（扫过 52 处）
- 否定/未实现声明：0 处（扫过 110 处）

结论：没找到证据（该补）

会被问：「SoftReadWriteLock 支持写者优先」对应的入口/路由与实现文件分别在哪里？能否给出一条可复现的调用？

该补什么：在 README 里给出该功能的入口定义与实现文件相对路径。

audit effort：5 类 340 处

### SoftReadWriteLock 提供无时钟心跳过期

来源：req-filelock-20.md#L19

查到：

- （无）

查过没找到：

- 路由/入口：0 处（扫过 88 处）
- 依赖声明：0 处（扫过 2 处）
- 相关实现：0 处（扫过 88 处）
- 测试覆盖：0 处（扫过 52 处）
- 否定/未实现声明：0 处（扫过 110 处）

结论：没找到证据（该补）

会被问：「SoftReadWriteLock 提供无时钟心跳过期」对应的入口/路由与实现文件分别在哪里？能否给出一条可复现的调用？

该补什么：在 README 里给出该功能的入口定义与实现文件相对路径。

audit effort：5 类 340 处

### AsyncFileLock 支持 async/await

来源：req-filelock-20.md#L20

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

会被问：「AsyncFileLock 支持 async/await」是在哪份压测脚本和哪种进程/线程配置下测得的？结果文件在哪里？

该补什么：无需补齐：证据已足够。

audit effort：5 类 507 处

### AsyncFileLock 支持自定义 executor 与事件循环

来源：req-filelock-20.md#L21

查到：

- 相关实现：2 处
  - tests/test_async_filelock_runner_shutdown.py:23
  - tests/test_async_filelock_transition_admission.py:31

查过没找到：

- 路由/入口：0 处（扫过 88 处）
- 依赖声明：0 处（扫过 2 处）
- 测试覆盖：0 处（扫过 52 处）
- 否定/未实现声明：0 处（扫过 110 处）

结论：有证据

会被问：「AsyncFileLock 支持自定义 executor 与事件循环」对应的入口/路由与实现文件分别在哪里？能否给出一条可复现的调用？

该补什么：无需补齐：证据已足够。

audit effort：5 类 340 处

### Windows 后端使用 LockFileEx 在字节范围上加锁

来源：req-filelock-20.md#L22

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

会被问：「Windows 后端使用 LockFileEx 在字节范围上加锁」对应的入口/路由与实现文件分别在哪里？能否给出一条可复现的调用？

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
