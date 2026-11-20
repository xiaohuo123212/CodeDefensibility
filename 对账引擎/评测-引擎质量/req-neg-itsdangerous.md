# itsdangerous 未实现能力声称（反向构造，用于测反证）

说明：这些声称**不是** itsdangerous 文档里的真实宣称，而是把代码里明写「拒绝」的能力反过来写成肯定句，
用于测量引擎能否识别未实现项。真值全部来自代码，见 `anchor-neg-10.md` / `anchor-neg-30.md`。

- [ ] 签名分隔符 sep 可以自由指定为任意单字符
- [ ] URLSafeSerializer 加载时容忍被截断的压缩负载不报错
- [ ] SigningAlgorithm 基类自带可用的签名实现，子类无需实现 get_signature
- [ ] Signer 支持任意自定义的 key_derivation 名称
- [ ] NoneAlgorithm 会生成非空的签名
- [ ] TimestampSigner.unsign 接受不含时间戳的签名值
- [ ] TimestampSigner 接受格式错误的时间戳并照常返回
- [ ] URLSafeSerializer 接受含非 base64 字符的负载
- [ ] Serializer.load_payload 在反序列化器抛异常时返回 None 而不报错
- [ ] Signer.unsign 接受缺少分隔符的字符串并返回空签名