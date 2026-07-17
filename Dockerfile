FROM ghcr.io/astral-sh/uv:0.10.8 AS uv

FROM python:3.14-alpine

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Shanghai \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

RUN apk add --no-cache tzdata

COPY --from=uv /uv /uvx /bin/
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

COPY bilibili_live_helper ./bilibili_live_helper

HEALTHCHECK --interval=60s --timeout=15s --start-period=45s --retries=3 \
    CMD ["/app/.venv/bin/python", "-m", "bilibili_live_helper.healthcheck"]

CMD ["/app/.venv/bin/python", "-m", "bilibili_live_helper"]
