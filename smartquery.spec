# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 打包配置
运行: pyinstaller smartquery.spec
"""

import os
import sys
from pathlib import Path

# 项目根目录
ROOT = Path(".").resolve()

# 收集 app/static 下所有文件
static_data = []
static_dir = ROOT / "app" / "static"
if static_dir.exists():
    for f in static_dir.rglob("*"):
        if f.is_file():
            dest = str(f.parent.relative_to(ROOT))
            static_data.append((str(f), dest))

a = Analysis(
    ['desktop_app.py'],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        # 静态资源
        ("app/static", "app/static"),
        # 环境变量模板（如果存在）
        *([(".env", ".")] if os.path.exists(".env") else []),
    ],
    hiddenimports=[
        "uvicorn.logging",
        "uvicorn.lifespan",
        "uvicorn.protocols",
        "fastapi",
        "sqlalchemy",
        "sqlparse",
        "openai",
        "pydantic",
        "dotenv",
        "app",
        "app.main",
        "app.database",
        "app.llm",
        "app.utils",
        "app.models",
        "app.prompts",
        "app.config",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "pandas",
        "numpy",
        "scipy",
        "PIL",
        "cv2",
        "tensorflow",
        "torch",
        "PyQt5",
        "PySide6",
        "PyQt6",
        "wx",
        "IPython",
        "jupyter",
        "notebook",
        "nbformat",
        "nbconvert",
        "sphinx",
        "docutils",
        "pytest",
        "black",
        "yapf",
        "zmq",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='SmartQuery',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,       # 保留控制台（用户需要看关闭提示）
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,           # 可替换为 .ico 文件路径
)
