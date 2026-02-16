# Use Python 3.11 slim image
FROM python:3.11-slim

# 1. Prevent the "debconf" error you saw earlier
ARG DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# 2. Install g++ (Critical for ChromaDB/LlamaIndex) and clean up apt cache to save space
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first for better caching
COPY backend/requirements.txt ./

# 3. Upgrade pip first, then install dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --no-warn-script-location -r requirements.txt

# Copy backend code
COPY backend .

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run FastAPI with uvicorn
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]