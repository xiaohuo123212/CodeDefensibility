#!/usr/bin/env bash
set -euo pipefail

# 容器内必须 headless + 0.0.0.0，否则只监听 127.0.0.1 且会尝试拉起浏览器
export STREAMLIT_SERVER_HEADLESS=true
export STREAMLIT_SERVER_ADDRESS=0.0.0.0
export STREAMLIT_SERVER_PORT="${GAP_DEMO_PORT:-8501}"
export STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# 反向代理 / 隧道把外部域名映射到容器时，Host 与来源不一致；
# 只放开 CORS，XSRF 保护保持开启（外网暴露时不建议关闭）。
export STREAMLIT_SERVER_ENABLE_CORS="${GAP_DEMO_ENABLE_CORS:-false}"
export STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION="${GAP_DEMO_ENABLE_XSRF:-true}"

cd "$(dirname "$0")/.."
exec streamlit run demo/app.py