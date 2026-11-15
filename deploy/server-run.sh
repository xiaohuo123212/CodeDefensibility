#!/usr/bin/env bash
# 在私网服务器上以「用户级 venv」启动 demo——适用于没有 Docker、sudo 需密码的机器。
#
# 前置（一次性，均不需要 sudo）：
#   cd gap-engine
#   python3 -m pip install --user --break-system-packages virtualenv
#   python3 -m virtualenv -p python3 .venv2
#   .venv2/bin/pip install -e ".[demo]"
#
# 用法：
#   bash deploy/server-run.sh                    # 默认 8501
#   GAP_DEMO_PORT=8600 bash deploy/server-run.sh  # 换端口
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_DIR="$REPO_ROOT/gap-engine"
PORT="${GAP_DEMO_PORT:-8501}"
VENV="${GAP_DEMO_VENV:-$APP_DIR/.venv2}"
LOG="${GAP_DEMO_LOG:-$HOME/gap-demo.log}"

cd "$APP_DIR"

if [ ! -x "$VENV/bin/streamlit" ]; then
  echo "找不到 $VENV/bin/streamlit" >&2
  echo "请先建环境并安装依赖：.venv2/bin/pip install -e \".[demo]\"" >&2
  exit 1
fi

# setsid 让进程脱离 SSH 会话，断开连接后继续运行
setsid "$VENV/bin/streamlit" run demo/app.py \
  --server.headless true \
  --server.address 0.0.0.0 \
  --server.port "$PORT" \
  --server.enableCORS false \
  --server.enableXsrfProtection false \
  --browser.gatherUsageStats false \
  > "$LOG" 2>&1 < /dev/null &

sleep 8
if curl -fsS --max-time 6 "http://127.0.0.1:$PORT/_stcore/health"; then
  echo " <- ok (port=$PORT log=$LOG)"
else
  echo "健康检查失败，最近日志：" >&2
  tail -20 "$LOG" >&2
  exit 1
fi