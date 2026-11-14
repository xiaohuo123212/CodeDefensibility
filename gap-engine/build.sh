#!/usr/bin/env bash
# Phase E / D0 轻量检查：仅编译检查，不执行测试套件。
set -e
cd "$(dirname "$0")"
python -m compileall -q src tests
echo "compile OK: src + tests"