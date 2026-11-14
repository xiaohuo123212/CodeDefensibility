# 公网 demo 镜像：在仓库根目录构建
#   docker build -f deploy/Dockerfile -t gap-demo:0.1.0 .
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# 先装引擎依赖，单独成层：后续改 demo/ 不必重装
COPY gap-engine/pyproject.toml ./pyproject.toml
COPY gap-engine/src ./src
RUN pip install -e ".[demo]"

# demo 与 fixture 仓库：app.py 的输入是「仓库路径」，容器内只带可演示的样本
COPY gap-engine/demo ./demo
COPY gap-engine/contract/fixtures ./contract/fixtures

COPY deploy/entrypoint.sh deploy/healthcheck.py ./deploy/
RUN chmod +x ./deploy/entrypoint.sh

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD ["python", "deploy/healthcheck.py"]

CMD ["bash", "deploy/entrypoint.sh"]