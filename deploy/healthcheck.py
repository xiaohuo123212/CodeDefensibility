"""容器健康检查：请求 Streamlit 内置健康端点，200 且 body 含 ok 才算健康。"""

from __future__ import annotations

import os
import sys
import urllib.error
import urllib.request

TIMEOUT_SECONDS = 3.0
DEFAULT_PORT = 8501


def resolve_port() -> int:
    raw = (
        os.environ.get("GAP_DEMO_PORT")
        or os.environ.get("STREAMLIT_SERVER_PORT")
        or str(DEFAULT_PORT)
    )
    try:
        return int(raw)
    except ValueError:
        return DEFAULT_PORT


def is_healthy(port: int) -> bool:
    url = f"http://127.0.0.1:{port}/_stcore/health"
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT_SECONDS) as response:
            body = response.read(64).decode("utf-8", "replace")
            return response.status == 200 and "ok" in body.lower()
    except (urllib.error.URLError, OSError):
        return False


def main() -> int:
    return 0 if is_healthy(resolve_port()) else 1


if __name__ == "__main__":
    sys.exit(main())