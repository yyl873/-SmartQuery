@echo off
chcp 65001 >nul
title SmartQuery - NL2SQL

echo.
echo   ╔══════════════════════════════════════════╗
echo   ║     🧠  SmartQuery  一键启动              ║
echo   ╚══════════════════════════════════════════╝
echo.

:: 安装/更新依赖
echo [1/3] 检查依赖...
pip install -r requirements.txt -q 2>nul
if %errorlevel% neq 0 (
    echo ⚠ pip 安装失败，尝试使用 pip3...
    pip3 install -r requirements.txt -q
)
echo ✅ 依赖就绪

:: 初始化数据库（如果不存在）
echo [2/3] 检查数据库...
if not exist "smartquery.db" (
    echo 📦 初始化示例数据库...
    python init_db.py
)
echo ✅ 数据库就绪

:: 启动服务
echo [3/3] 启动服务...
echo.
echo   ┌──────────────────────────────────────────┐
echo   │  浏览器访问: http://localhost:8000        │
echo   │  按 Ctrl+C 停止服务                       │
echo   └──────────────────────────────────────────┘
echo.

start http://localhost:8000
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

pause
