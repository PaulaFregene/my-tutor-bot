# Use Python 3.11 slim image
FROM python:3.11-slim

ARG DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# 1. Install System Deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 2. Install CPU Torch (Lightweight)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# --- THE LADDER STRATEGY ---

# 3. [LADDER STEP 1] Install ChromaDB
RUN pip install --no-cache-dir chromadb llama-index-vector-stores-chroma

# 4. [LADDER STEP 2] Install HuggingFace
RUN pip install --no-cache-dir llama-index-embeddings-huggingface

# 5. [LADDER STEP 3] Install the rest of LlamaIndex
RUN pip install --no-cache-dir llama-index-core llama-index-llms-groq

# ---------------------------

# 6. Install the rest of your requirements
COPY requirements.txt .
RUN pip install --no-cache-dir --no-warn-script-location -r requirements.txt

# 7. Copy Code & Start
COPY . .

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
