# 公网 demo 部署物料

目标：把 `gap-engine/demo/app.py`（Streamlit）从私网服务器暴露成评审可打开的公网 URL。

**本目录只给物料与步骤，不代表已经部署成功。** 所有命令都要在指定机器上由你执行：

| 机器 | 角色 | 谁执行 |
| --- | --- | --- |
| 你的私网服务器 | 跑容器 / 跑 streamlit | 你（本机或 SSH 到私网服务器） |
| Cloudflare 边缘 | 路径 A，无需公网云服务器 | Cloudflare 提供 |
| 华为云 ECS | 路径 B，需要买一台带公网 IP 的机器 | 你（华为云控制台） |
| 中转机 | 路径 C，需要一台带公网 IP 的机器 | 你 |

## 0. 通用前置：构建镜像（在私网服务器上）

假设仓库在私网服务器的 `~/CodeDefensibility`：

```bash
cd ~/CodeDefensibility
docker build -f deploy/Dockerfile -t gap-demo:0.1.0 .
docker run -d --name gap-demo --restart unless-stopped -p 8501:8501 gap-demo:0.1.0
docker logs -f gap-demo
```

本机自检（镜像健康检查与端口都在容器内闭环）：

```bash
curl -fsS http://127.0.0.1:8501/_stcore/health   # 期望 200，body 为 ok
docker inspect --format '{{.State.Health.Status}}' gap-demo   # 期望 healthy
```

改端口时两者一起改，入口脚本支持 `GAP_DEMO_PORT` 覆盖：

```bash
docker run -d --name gap-demo -e GAP_DEMO_PORT=8600 -p 8600:8600 gap-demo:0.1.0
```

没装 Docker 时的退路（仅私网服务器本机可跑通，公网仍需隧道/反代）：

```bash
cd ~/CodeDefensibility/gap-engine
python -m venv .venv && . .venv/bin/activate
pip install -e ".[demo]"
STREAMLIT_SERVER_HEADLESS=true STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
  streamlit run demo/app.py --server.port 8501
```

---

## 路径 A（推荐）：私网服务器 + Cloudflare Tunnel

不需要公网云服务器、不需要公网 IP、不用改安全组。私网服务器主动向 Cloudflare 建出站连接。

### A1. 临时域名（最快，几分钟）

前置：私网服务器能访问外网 443；容器已在 8501 端口跑起来。

```bash
# 私网服务器上安装 cloudflared（Debian/Ubuntu 示例，其他系统见官方文档）
curl -L -o cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared.deb

# 起一个临时隧道，输出里会打印 https://<随机名>.trycloudflare.com
cloudflared tunnel --url http://localhost:8501
```

拿到 `https://xxx.trycloudflare.com` 后，在手机 4G / 外部网络打开验证，然后写进提交材料。

### A2. 命名隧道（域名固定，适合评审期间稳定使用）

前置：一个托管在 Cloudflare 的域名（免费套餐即可）。

```bash
cloudflared tunnel login                       # 浏览器授权域名
cloudflared tunnel create gap-demo             # 生成隧道凭据
cloudflared tunnel route dns gap-demo demo.example.com
cloudflared tunnel run --url http://localhost:8501 gap-demo
```

常驻可用 systemd（`/etc/systemd/system/gap-demo-tunnel.service`，`ExecStart=/usr/bin/cloudflared tunnel run --url http://localhost:8501 gap-demo`），或直接 `nohup cloudflared tunnel run --url http://localhost:8501 gap-demo &`。

### A3. 免费版限制与稳定性（评审前必须知道）

- 临时隧道（trycloudflare.com）：**每次重启换域名**，官方定位为测试用途，**无 SLA、随时可能断开**；域名不能自定义。
- 命名隧道：需要自有域名接入 Cloudflare；免费套餐足够跑单条隧道，但**无 SLA**，Cloudflare 侧抖动会影响可用性。
- WebSocket（Streamlit 必需）在免费套餐下可用；免费套餐有单请求体积上限（大文件上传会被拒），demo 只传路径字符串，不受影响。
- 免费额度的确切数值以 Cloudflare 官方文档为准，不要写进提交材料当承诺。
- 隧道只把 **8501 的 HTTP** 暴露出去，容器端口本身**不要**再 `-p` 映射到公网网卡（保持 `-p 127.0.0.1:8501:8501` 更安全）。

### A4. 失效回退

1. 隧道断了：重跑 `cloudflared tunnel --url http://localhost:8501`，把新 URL 更新到 readme/PPT；临时域名换名属于预期行为。
2. Cloudflare 整体不可用：切路径 B（ECS + nginx）或路径 C（frp），URL 换成自有域名/IP。
3. 只想先让评审看到：录屏 + 本地截图作为兜底材料，同时在提交材料里写明「现场 demo 需公网 URL」。

---

## 路径 B：华为云 ECS + nginx 反向代理

前置：华为云 ECS（1C2G 起）、公网 IP 或绑定域名、已备案域名（大陆节点 80/443 必须备案）。

### B1. 启动容器

```bash
# ECS 上
git clone <你的仓库地址> ~/CodeDefensibility && cd ~/CodeDefensibility
docker build -f deploy/Dockerfile -t gap-demo:0.1.0 .
docker run -d --name gap-demo --restart unless-stopped -p 127.0.0.1:8501:8501 gap-demo:0.1.0
curl -fsS http://127.0.0.1:8501/_stcore/health
```

### B2. 安全组

- 入方向放行 TCP **80 / 443**（0.0.0.0/0）。
- **不要**放行 8501；容器只绑 `127.0.0.1`，由 nginx 回源。
- 出方向保持默认放行（拉镜像、装包需要）。

### B3. nginx 反向代理（`/etc/nginx/conf.d/gap-demo.conf`）

```nginx
server {
    listen 80;
    server_name demo.example.com;

    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        # Streamlit 走 WebSocket，缺这两行会出现「一直 Connecting」
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 3600s;
        proxy_buffering off;
    }
}
```

```bash
sudo nginx -t && sudo systemctl reload nginx
curl -fsS http://demo.example.com/_stcore/health
```

### B4. SSL

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d demo.example.com     # 自动改 443 并续期
```

### B5. 失效回退

- nginx 502：`docker ps` 看容器是否退出，`docker logs gap-demo`；回退成 `-p 8501:8501` 直连验证是容器问题还是反代问题。
- WebSocket 失败（页面一直 Connecting）：确认 `Upgrade`/`Connection` 两行；再确认安全组/云厂商 WAF 没拦 WebSocket。
- 证书过期：`sudo certbot renew --dry-run` 排查。
- 费用/时间不够：退到路径 A（Cloudflare Tunnel），ECS 只用来跑容器甚至不用买。

---

## 路径 C：frp 自建（需一台有公网 IP 的中转机）

前置：一台带公网 IP 的中转机（ECS/轻量云均可）+ 私网服务器；中转机开放 7000（frps）与 8080（对外映射端口）。

```bash
# 中转机：frps.toml
bindPort = 7000
auth.token = "换成随机串"

# 私网服务器：frpc.toml
serverAddr = "<中转机公网IP>"
serverPort = 7000
auth.token = "换成随机串"

[[proxies]]
name = "gap-demo"
type = "tcp"
localIP = "127.0.0.1"
localPort = 8501
remotePort = 8080
```

```bash
# 中转机
./frps -c frps.toml
# 私网服务器（容器先跑在 127.0.0.1:8501）
./frpc -c frpc.toml
# 验证
curl -fsS http://<中转机公网IP>:8080/_stcore/health
```

注意：走 HTTP 明文，若对外给评审用，建议在中转机再加 nginx + 证书（同路径 B3/B4），或在 frp 上叠 TLS。失效回退：frpc 掉线就重启；中转机不可用时切路径 A。

---

## Streamlit 关键配置（三条路径通用）

- 必须 `STREAMLIT_SERVER_HEADLESS=true`：否则启动时会试开浏览器，容器里直接报错。
- 必须 `STREAMLIT_SERVER_ADDRESS=0.0.0.0`：监听 127.0.0.1 时隧道/反代回源会连不上。
- `STREAMLIT_BROWSER_GATHER_USAGE_STATS=false`：不在公网环境回传统计。
- CORS/XSRF：`deploy/entrypoint.sh` 默认 `ENABLE_CORS=false`、`ENABLE_XSRF_PROTECTION=true`。外部域名与容器 Host 不一致时，若页面报 CORS/WebSocket 403，先确认反代是否转发 `Host` 与 `Upgrade`；只在确认是来源校验导致时才临时 `-e GAP_DEMO_ENABLE_XSRF=false`，并知悉这会降低外网防护。
- 健康端点固定为 `/_stcore/health`，返回 body `ok`；`deploy/healthcheck.py` 与 Docker `HEALTHCHECK` 都打它。
- demo 的输入是「仓库路径 / 需求清单路径」，容器内可演示样本在 `/app/contract/fixtures/fx-spec` 等目录，页面里填这个路径即可。

---

## 提交材料怎么写

采用公网 demo 时，`readme/` 与 `ppt/PPT大纲.md` 只写**已发生的事实**：

1. **公网 URL**：写实际可访问的地址（如 `https://xxx.trycloudflare.com` 或 `https://demo.example.com`），并注明「临时域名，重启隧道会变化」。
2. **启动命令**：写清在哪台机器执行什么命令，例如
   `私网服务器：cd ~/CodeDefensibility && docker build -f deploy/Dockerfile -t gap-demo:0.1.0 . && docker run -d -p 127.0.0.1:8501:8501 gap-demo:0.1.0`
   以及隧道命令 `cloudflared tunnel --url http://localhost:8501`。
3. **限制声明**：写明「demo 运行在私网服务器 + Cloudflare 隧道/自建反代上，非生产部署；无 SLA；单实例；隧道重启后 URL 可能变化；仅用于评审演示」。
4. **不要写**「已生产部署」「高可用」「已上线服务」「支持并发多租户」这类没有实测支撑的说法；不要把 Cloudflare 免费额度写成承诺。
5. 附一条自检证据：`curl -fsS <公网URL>/_stcore/health` 返回 `ok` 的截图或文本，放在 `codearts_proof/` 下。

---

## 本次物料的验证范围

- 已做：`deploy/healthcheck.py` 与 `deploy/entrypoint.sh` 的语法级检查（`py_compile` / `bash -n`）。
- 未实机验证（当前环境无 Docker、也接触不到你的私网服务器）：`docker build`、容器启动、`nginx -t`、`certbot`、`cloudflared`/`frp` 隧道连通性、公网 URL 可达性。以上必须在私网服务器 / ECS 上按本文命令自行跑一遍，并把结果写回提交材料。