FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir ".[server]"

COPY deploy/control-plane/autoforge.yaml ./autoforge.yaml
COPY deploy/postgresql/init ./deploy/postgresql/init
RUN mkdir -p /workspace/output

ENTRYPOINT ["python", "-m", "autoforge.main"]
CMD ["server", "--config", "/app/autoforge.yaml", "--source-root", "/workspace", "--output-root", "/workspace/output", "--host", "0.0.0.0", "--port", "8000"]
