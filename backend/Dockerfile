FROM python:3.11-slim

# System deps: gcc for pycparser, libpq for psycopg2, curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        cpp \
        g++ \
        libpq-dev \
        curl \
        git \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Docker CLI so the backend can spin up sandbox containers
RUN curl -fsSL https://get.docker.com | sh

WORKDIR /app

# Install Python deps first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Uploads directory
RUN mkdir -p /app/uploads

# Non-root user for the API (sandbox worker still needs docker socket)
RUN groupadd -r appuser && useradd -r -g appuser -m appuser \
 && chown -R appuser:appuser /app

EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]