# =============================================================================
# Aegis AI - Secure AI Gateway
# Production Dockerfile
# =============================================================================
# This Dockerfile builds a production-ready container for Aegis AI.
# 
# Build:
#   docker build -t aegis-ai .
#
# Run:
#   docker-compose up -d
#
# First launch: Complete the Setup Wizard in the browser.
# Admin password, AIDR tokens, and AI provider are configured via the wizard.
# =============================================================================

FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set working directory
WORKDIR /app

# Install system dependencies required for some Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libpq-dev \
    libmagic1 \
    poppler-utils \
    tesseract-ocr \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js v22+ for MCP proxy
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY frontend/ ./frontend/
COPY main.py .
COPY scripts/ ./scripts/
COPY mcp_server/ ./mcp_server/
COPY requirements.txt .

# Create data directory for persistent storage
RUN mkdir -p /app/data /app/mcp_workspace/documents /app/mcp_workspace/data \
    /app/mcp_workspace/temp /app/mcp_workspace/logs /app/mcp_workspace/scripts \
    && chmod -R 777 /app/mcp_workspace

# Set the data directory environment variable
ENV DATA_DIR=/app/data
ENV MCP_WORK_DIR=/app/mcp_workspace

# Expose the application port
EXPOSE 15000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:15000/api/health || exit 1

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "15000"]
