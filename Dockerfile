FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gammu \
    libgammu-dev \
    pkg-config \
    python3-dev \
    gcc \
    sqlite3 \
    gosu \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create gammu user and add to dialout group
RUN useradd -m -u 101 -G dialout gammuuser

# Set up working directory
WORKDIR /app

# Create necessary directories with proper permissions
RUN mkdir -p /app/instance /app/logs /app/database && \
    chown -R gammuuser:dialout /app/instance /app/logs && \
    chmod 775 /app/instance /app/logs && \
    chmod 755 /app/database

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Set up permissions
RUN chown -R gammuuser:dialout /app && \
    chmod +x entrypoint.sh

# Create Gammu config
RUN echo "[gammu]\ndevice = /dev/ttyUSB3\nconnection = at\nmodel = auto" > /etc/gammurc && \
    mkdir -p /home/gammuuser/.config/gammu && \
    cp /etc/gammurc /home/gammuuser/.config/gammu/config && \
    chown -R gammuuser:dialout /home/gammuuser/.config

# Switch to non-root user
USER gammuuser

# Set entrypoint
ENTRYPOINT ["./entrypoint.sh"] 