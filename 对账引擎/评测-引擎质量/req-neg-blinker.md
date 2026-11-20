# blinker 未实现能力声称（反向构造，用于测反证）

说明：这些声称**不是** blinker 文档里的真实宣称，而是把代码里明写「做不到」的能力反过来写成肯定句，
用于测量引擎能否识别未实现项。真值全部来自代码，见 `anchor-neg-10.md` / `anchor-neg-30.md`。

- [ ] Signal.send 支持向异步协程订阅者发送事件
- [ ] Signal.send_async 支持向同步函数订阅者发送事件
- [ ] receiver_disconnected 会在弱引用接收者被回收时自动触发
- [ ] Signal.has_receivers_for 会排除已被回收的弱引用接收者
- [ ] Signal 的簿记剪枝在多线程并发 connect/disconnect 下是线程安全的