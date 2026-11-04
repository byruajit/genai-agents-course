# The LiteLLM proxy as a container. We build it ourselves from a pinned version (same as the course: 1.80.0).
FROM python:3.12-slim
RUN pip install --no-cache-dir "litellm[proxy]==1.80.0"
WORKDIR /app
EXPOSE 4000
# config.yaml is mounted by docker-compose.yml, so you can edit it without rebuilding
CMD ["litellm", "--config", "/app/config.yaml", "--host", "0.0.0.0", "--port", "4000"]
