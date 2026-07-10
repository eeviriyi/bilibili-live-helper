FROM ghcr.io/astral-sh/uv:0.10.8 AS uv

FROM python:3.14-alpine

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Shanghai \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

COPY --from=uv /uv /uvx /bin/
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

COPY fans_medal_helper ./fans_medal_helper

CMD ["/app/.venv/bin/python", "-m", "fans_medal_helper"]
