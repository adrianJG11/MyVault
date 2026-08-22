FROM ghcr.io/astral-sh/uv:0.12.5-python3.14-trixie-slim

WORKDIR /app

ENV UV_NO_DEV=1

COPY pyproject.toml uv.lock ./

RUN uv sync --locked --no-install-project

COPY . .

RUN useradd --create-home --uid 10001 --user-group appuser

USER appuser

CMD ["/app/.venv/bin/fastapi", "run", "main.py", "--host", "0.0.0.0", "--port", "8000"]