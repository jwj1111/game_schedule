# ============================================================
# 后端运行环境（基于 Playwright 官方镜像，自带 Chromium）
# ============================================================
FROM mcr.microsoft.com/playwright/python:v1.49.1-noble

WORKDIR /app

# 安装 Python 依赖
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制后端代码
COPY backend/ ./backend/

# 复制 .env.example 作为默认配置参考
COPY .env.example ./.env.example

# 创建数据目录和日志目录
RUN mkdir -p /app/data /app/logs

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["python", "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
