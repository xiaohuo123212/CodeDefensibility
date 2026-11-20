# filelock 未实现能力声称（反向构造，用于测反证）

说明：这些声称**不是** filelock 文档里的真实宣称，而是把代码里明写「不支持」的能力反过来写成肯定句，
用于测量引擎能否识别未实现项。真值全部来自代码，见 `anchor-neg-10.md` / `anchor-neg-30.md`。

- [ ] AsyncFileLock 支持用同步 with 语句加锁
- [ ] FileLock 支持用 lifetime 参数按文件年龄强制过期
- [ ] SoftFileLock 支持 preserve_lock_file=True 保留锁文件不删
- [ ] 所有锁类型都支持 on_acquired 回调拿到文件描述符
- [ ] 同一个锁类允许用不同参数创建多个单例实例
- [ ] AsyncFileLock 在 thread_local=True 时仍支持 run_in_executor=True
- [ ] SoftFileLock 支持非默认的锁选项（如 thread_local=True）
- [ ] FileLock 在 fork 出的子进程里可以直接复用父进程构造的实例
- [ ] ReadWriteLock 单例允许用不同的 timeout 和 blocking 复用同一实例
- [ ] preserve_lock_file=True 能阻止其它进程删除锁文件路径
- [ ] fallback_to_soft 参数在 Windows 平台上同样生效
- [ ] StrictSoftFileLock 的 lifetime 参数能按文件年龄清除陈旧声明
- [ ] SoftFileLock 在 Windows 上释放时会立即删除锁文件