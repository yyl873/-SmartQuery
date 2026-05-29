# ============================================================
# SmartQuery Dockerfile
#   docker build -t smartquery .
#   docker run -p 8000:8000 --env-file .env smartquery
# ============================================================

FROM python:3.12-slim

WORKDIR /app

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY app/ ./app/
COPY init_db.py .

# 预初始化示例数据库（可选）
RUN python init_db.py 2>/dev/null; exit 0

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
