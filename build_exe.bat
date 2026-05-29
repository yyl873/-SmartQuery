@echo off
chcp 65001 >nul
echo ==================================================
echo   🧠 SmartQuery EXE 打包工具
echo ==================================================
echo.

:: 检查 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 未找到 Python，请先安装 Python 3.10+
    pause
    exit /b 1
)

:: 安装依赖
echo 📦 安装项目依赖...
pip install -r requirements.txt -q
if %errorlevel% neq 0 (
    echo ❌ 依赖安装失败
    pause
    exit /b 1
)

:: 安装 PyInstaller
echo 📦 安装 PyInstaller...
pip install pyinstaller -q
if %errorlevel% neq 0 (
    echo ❌ PyInstaller 安装失败
    pause
    exit /b 1
)

:: 打包
echo 🔨 开始打包（可能需要 2-5 分钟）...
echo.
pyinstaller smartquery.spec --clean --noconfirm

if %errorlevel% equ 0 (
    echo.
    echo ==================================================
    echo   ✅ 打包完成！
    echo.
    echo   EXE 位置: dist\SmartQuery.exe
    echo   大小:
    dir dist\SmartQuery.exe 2>nul | find "SmartQuery.exe"
    echo.
    echo   双击 dist\SmartQuery.exe 即可运行
    echo ==================================================
) else (
    echo.
    echo ❌ 打包失败，请检查上方错误信息
)

pause
