# The app as a container. Note what is NOT here: no API key, no .env - keys come in at run time.
FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir "fastapi==0.162.0" "uvicorn==0.54.0" "langchain-openai==1.1.9" "openai>=1.60,<2"
COPY app.py .
EXPOSE 8000
# 0.0.0.0 = listen on every network interface, so traffic from outside the container can reach it
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
