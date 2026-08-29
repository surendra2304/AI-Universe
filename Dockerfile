# Multi-stage production Dockerfile for AI Universe (Optimized for Hugging Face Spaces & Cloud)
FROM python:3.11-slim as builder

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc python3-dev && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.11-slim

WORKDIR /app

# Create non-root user with UID 1000 required by Hugging Face Spaces
RUN useradd -m -u 1000 user && \
    mkdir -p /app/data && \
    chown -R user:user /app

COPY --from=builder --chown=user:user /root/.local /home/user/.local
COPY --chown=user:user . /app

USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PORT=7860

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:7860/health').read()" || exit 1

EXPOSE 7860
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "4"]
