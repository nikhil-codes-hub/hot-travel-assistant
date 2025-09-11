# Docker-compatible Python backend Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables for Docker
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV PORT=8080

# Install system dependencies (Docker-compatible)
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    pkg-config \
    default-libmysqlclient-dev \
    python3-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies with Docker-compatible flags
RUN pip install --no-cache-dir --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt

# Copy the backend application
COPY . .

# Create necessary directories
RUN mkdir -p cache/llm_responses
RUN mkdir -p logs

# Verify the structure (for debugging)
RUN ls -la /app/api/

# Create non-root user for Docker security best practices
RUN groupadd -r appuser && useradd -r -g appuser appuser
RUN chown -R appuser:appuser /app
USER appuser

# Expose port (Cloud Run uses PORT env var)
EXPOSE $PORT

# Health check (Docker-compatible)
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:$PORT/health || exit 1

# Start the application with proper Docker CMD format
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT}"]