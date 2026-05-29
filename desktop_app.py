"""
SmartQuery 桌面启动器
双击 EXE 后自动启动服务器并打开浏览器
"""

import os
import sys
import time
import socket
import threading
import webbrowser

# ---- 路径处理 ----
if getattr(sys, 'frozen', False):
    # PyInstaller 打包后
    APP_DIR = os.path.dirname(sys.executable)          # EXE 所在目录（可写）
    RESOURCE_DIR = sys._MEIPASS                         # 临时解压目录（只读）
else:
    # 开发模式
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
    RESOURCE_DIR = APP_DIR

# 工作目录切换到 APP_DIR，确保 .env / 数据库文件生成在 EXE 旁边
os.chdir(APP_DIR)

# 确保资源目录在 sys.path 中，app 模块能正确导入
if RESOURCE_DIR not in sys.path:
    sys.path.insert(0, RESOURCE_DIR)


def find_free_port(start=8000, end=8100):
    """找一个可用的端口，避免冲突"""
    for port in range(start, end):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('127.0.0.1', port)) != 0:
                return port
    return 8000


def check_env():
    """检查 .env 文件，不存在则提示"""
    env_path = os.path.join(APP_DIR, ".env")
    if not os.path.exists(env_path):
        print("⚠️  未找到 .env 配置文件")
        print(f"   请在 {APP_DIR} 目录下创建 .env 文件，内容示例：")
        print()
        print("   LLM_API_KEY=sk-your-api-key-here")
        print("   LLM_BASE_URL=https://api.openai.com/v1")
        print("   LLM_MODEL=gpt-3.5-turbo")
        print()
        print("   如未配置 LLM，SQL 生成功能将不可用。")
        print("   数据库查询功能不受影响。")
        print("-" * 50)
        return False
    return True


def main():
    import uvicorn

    port = find_free_port()
    url = f"http://127.0.0.1:{port}"

    print()
    print("=" * 50)
    print("   🧠 SmartQuery - NL2SQL 智能查询")
    print("=" * 50)
    print(f"   本地地址: {url}")
    print(f"   数据目录: {APP_DIR}")
    print()

    check_env()

    print("   正在启动服务...")
    print("   浏览器将自动打开，关闭本窗口即可退出")
    print("=" * 50)
    print()

    # 启动 FastAPI 服务器（后台线程）
    def run_server():
        uvicorn.run(
            "app.main:app",
            host="127.0.0.1",
            port=port,
            log_level="warning",
            reload=False,
        )

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    # 等待服务器就绪
    time.sleep(1.5)

    # 自动打开浏览器
    webbrowser.open(url)

    # 保持主线程运行
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n正在关闭 SmartQuery...")
        sys.exit(0)


if __name__ == "__main__":
    main()
