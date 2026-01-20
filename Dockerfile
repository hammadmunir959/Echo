# Stage 1: Builder
FROM python:3.10-slim-bullseye as builder

WORKDIR /app
COPY requirements.txt .

# Install build deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install python deps to /install
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: Runtime (The Potato Image)
FROM python:3.10-slim-bullseye

WORKDIR /app

# Install Runtime Deps (FFmpeg is MUST)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed python packages
COPY --from=builder /install /usr/local

# Copy Source Code
COPY . .

# Create directories for persistence
RUN mkdir -p database recordings models

# Set default env
ENV PYTHONUNBUFFERED=1

# Default command (overridden by compose)
CMD ["python", "runners/api_server.py"]
