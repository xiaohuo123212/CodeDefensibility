# filelock 需求对账报告

这是 spec 模式：报告只说明我查过哪里，不说明你没做过。

## 需求可判定性预检

共 5 条需求，5 条可判定，0 条无法验收。

## 项目实际是什么

- 文件 110 个，代码 9883 行
- 入口：未识别到启动入口
- 依赖：cachetools==7.2.7 \, colorama==0.4.6 \, distlib==0.4.4 \, filelock==4.2.4 \, packaging==26.3 \
- 测试：40 个测试文件
- 一句话：未识别到启动入口；依赖 12 个（cachetools==7.2.7 \, colorama==0.4.6 \）；40 个测试文件。

## 概览

#### 查过 1700 处（5 条需求，5 类探测项）

- 其中不同位置 340 处（同一探测项被多条需求重复扫描时只计一次）

- 有证据 2 条 / 没找到证据 2 条 / 有反证 1 条

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

## 未覆盖

- 无

## 局限

- 本批只跑单轮检索，多轮换假设未启用。
- 只把显式否定声明当反证：没有显式否定时不下断言。
- 缺口判定依赖先验普遍性表（PREVALENCE），尚未用同类项目实测。
- 规则优先，LLM 默认关闭；分类歧义未做消解。
- 报告只反映我查过的位置，不等于你没做过。
- spec 模式的补齐物生成与多轮换假设尚未启用。
