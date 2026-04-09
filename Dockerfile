# 后端 API Dockerfile（项目根目录）
# 此文件会自动被 Zeabur 检测到

FROM python:3.11-slim as builder

WORKDIR /app

# 安装构建依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖到虚拟环境
COPY requirements.txt .
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir -r requirements.txt

# 运行阶段
FROM python:3.11-slim as runtime

# 安装运行时依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    fonts-noto-cjk \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 创建非 root 用户
RUN groupadd -r appgroup && useradd -r -g appgroup appuser

WORKDIR /app

# 从构建阶段复制虚拟环境
COPY --from=builder /opt/venv /opt/venv

# 设置 PATH 使用虚拟环境
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# 复制应用代码
COPY --chown=appuser:appgroup . .

# 创建必要的目录
RUN mkdir -p /app/data/uploads && chown -R appuser:appgroup /app/data

# 切换到非 root 用户
USER appuser

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

EXPOSE ${PORT:-8000}

# 使用 gunicorn 生产级服务器（使用 shell 展开环境变量）
# 注意：使用 1 个 worker 以最小化内存占用（约 100-150MB）
# Zeabur 免费套餐内存限制 440MB，单 worker 最安全
CMD ["sh", "-c", "gunicorn apps.api.main:app -w 1 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:${PORT:-8000} --timeout 120 --access-logfile - --error-logfile -"]
