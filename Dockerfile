# Use Python 3.11 slim image
FROM python:3.11-slim

ARG DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./

# 1. Install CPU-only PyTorch first (Shrinks image by ~1.5GB)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# 2. Then install the rest (using the lightweight torch we just installed)
RUN pip install --no-cache-dir --no-warn-script-location -r requirements.txt

COPY backend .

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
