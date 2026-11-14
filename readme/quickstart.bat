@echo off
rem 一键安装 + 冒烟验证（Windows）。在任意目录双击或命令行执行均可。
rem 不联网建仓库、不执行被测仓库代码、不装被测仓库依赖。
setlocal enabledelayedexpansion
cd /d "%~dp0.."

if "%PYTHON%"=="" set "PYTHON=python"

echo [1/3] 安装（可编辑模式，运行时零第三方依赖）
"%PYTHON%" -m pip install -e gap-engine || exit /b 1

echo [2/3] 验证入口
gap --help || exit /b 1

echo [3/3] 冒烟：对反证 fixture 跑一份报告
set "OUT=%TEMP%\gap-quickstart-check.md"
gap spec gap-engine\contract\fixtures\fx-contradicted --spec gap-engine\contract\fixtures\fx-contradicted\requirements.md --out "%OUT%" || exit /b 1

echo --- 期望出现这两行 ---
echo 结论：代码里有反证，与要求不一致
echo 定位：app.py:9
echo --- 实际 ---
findstr /C:"结论：代码里有反证" /C:"- 定位：app.py:9" "%OUT%" || exit /b 1

echo OK：报告已生成于 %OUT%
exit /b 0