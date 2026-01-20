# Stage 1: Build dependencies
FROM python:3.12-slim-bookworm AS builder

# Prevent python from producing pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install build-time dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libasound2-dev \
    portaudio19-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies into a virtualenv for easy transfer
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Final minimal image
FROM python:3.12-slim-bookworm

WORKDIR /app

# Install only essential runtime libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libportaudio2 \
    libasound2 \
    libgomp1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy the virtualenv from the builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy source code (using .dockerignore effectively)
COPY api/ ./api/
COPY core/ ./core/
COPY database/ ./database/
COPY runners/ ./runners/

# Create necessary directories
RUN mkdir -p recordings models

# Expose API port
EXPOSE 8080

# Use the virtualenv's python
CMD ["python", "runners/api_server.py", "--port", "8080"]
