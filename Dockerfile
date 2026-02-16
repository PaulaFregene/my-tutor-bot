# Use Python 3.11 slim image
FROM python:3.11-slim

ARG DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# 1. Install System Deps (g++ is needed for ChromaDB)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 2. Install CPU Torch (Lightweight)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# 3. Install Heavy AI Libraries manually
# Removed these from requirements.txt, so we MUST install them here.
RUN pip install --no-cache-dir \
    chromadb \
    llama-index-core \
    llama-index-llms-groq \
    llama-index-embeddings-huggingface \
    llama-index-vector-stores-chroma

# 4. Copy requirements and install the rest (FastAPI, etc.)
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir --no-warn-script-location -r requirements.txt

# 5. Copy Backend Code
COPY backend .

EXPOSE 8000

# Health check to ensure app is running
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start the app
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
