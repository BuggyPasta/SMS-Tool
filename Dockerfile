FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gammu \
    libgammu-dev \
    pkg-config \
    python3-dev \
    gcc \
    sqlite3 \
    curl \
    net-tools \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy application files
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create necessary directories
RUN mkdir -p /app/instance /app/logs

# Set entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
