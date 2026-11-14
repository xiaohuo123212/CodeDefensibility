#!/usr/bin/env bash
# 一键安装 + 冒烟验证（在仓库根或 readme/ 下执行均可）
# 用途：干净环境验证「装得上、跑得出报告」。不联网、不执行被测仓库代码、不装被测仓库依赖。
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PY="${PYTHON:-python}"

echo "[1/3] 安装（可编辑模式，运行时零第三方依赖）"
"$PY" -m pip install -e gap-engine

echo "[2/3] 验证入口"
gap --help

echo "[3/3] 冒烟：对反证 fixture 跑一份报告"
OUT="${TMPDIR:-/tmp}/gap-quickstart-check.md"
gap spec gap-engine/contract/fixtures/fx-contradicted \
  --spec gap-engine/contract/fixtures/fx-contradicted/requirements.md \
  --out "$OUT"

echo "--- 期望出现这两行 ---"
echo "结论：代码里有反证，与要求不一致"
echo "定位：app.py:9"
echo "--- 实际 ---"
grep -E "^(结论：代码里有反证|.*- 定位：app\.py:9)" "$OUT"

echo "OK：报告已生成于 $OUT"