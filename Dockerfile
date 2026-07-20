# =============================================================================
# Aegis AI - Secure AI Gateway
# Production Dockerfile
# =============================================================================
#
# Build:
#   docker build -t aegis-ai .
#
# Run:
#   docker-compose up -d
#
# First launch: Open http://localhost:15000 and complete the Setup Wizard.
# Admin password, AIDR tokens, and AI provider are configured via the wizard.
# =============================================================================

FROM python:3.12-slim

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system dependencies required for document/media processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libpq-dev \
    libmagic1 \
    poppler-utils \
    tesseract-ocr \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js v22 for CrowdStrike MCP proxy (npx @crowdstrike/aidr-mcp-proxy)
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY app/ ./app/
COPY frontend/ ./frontend/
COPY main.py .
COPY mcp_server/ ./mcp_server/

# Create data directories for persistent storage (mounted as volumes)
RUN mkdir -p /app/data /app/mcp_workspace/documents /app/mcp_workspace/data \
    /app/mcp_workspace/temp /app/mcp_workspace/logs /app/mcp_workspace/scripts \
    && chmod -R 777 /app/mcp_workspace

# Environment variables (override via docker-compose or .env)
ENV DATA_DIR=/app/data
ENV MCP_WORK_DIR=/app/mcp_workspace

EXPOSE 15000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:15000/api/health || exit 1

# Run with uvicorn (production ASGI server)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "15000"]
