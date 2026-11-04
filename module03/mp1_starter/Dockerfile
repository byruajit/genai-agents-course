# ShopAssist - one container image: Python, the pinned packages, your code, your prompt and the store data.
# NOT your .env: keys arrive at run time (docker-compose.yml: env_file).
#   everything:  docker compose up --build
#   app only:    docker build -t shopassist .   then   docker run --rm -p 8000:8000 --env-file .env shopassist
#                (the gateway must be reachable: set GATEWAY_URL=http://host.docker.internal:4000 with -e)

FROM python:3.12-slim

# uv, pinned, from PyPI (the same tool you've used since Session 2)
RUN pip install --no-cache-dir uv==0.12.19

WORKDIR /app

# 1) dependencies first: this layer is cached, so changing your code doesn't reinstall everything
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# 2) then your code, your prompt and the store data
COPY app ./app
COPY prompts ./prompts
COPY data ./data

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

EXPOSE 8000

# Docker asks /health every 30s; `docker ps` shows "healthy" or "unhealthy"
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4)"

# 0.0.0.0, not 127.0.0.1: listen on the container's network so the port mapping can reach it
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
