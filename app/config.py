"""
SmartQuery 配置模块
加载环境变量并导出应用配置
"""

import os
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
load_dotenv()

# 数据库连接 URL，默认使用 SQLite
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")

# LLM API 密钥（必填）
LLM_API_KEY = os.getenv("LLM_API_KEY", "")

# LLM API 基础地址，兼容 OpenAI / DeepSeek 等
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")

# LLM 模型名称
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
