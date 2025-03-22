FROM python:3.11-slim

# Install dependencies
RUN apt-get update && apt-get install -y \
    gammu libgammu-dev pkg-config python3-dev gcc sqlite3 curl \
    && rm -rf /var/lib/apt/lists/*

# Create gammu user and add to dialout group
RUN useradd -m -u 101 -G dialout gammuuser

WORKDIR /app

# Copy application
COPY . .
RUN pip install --no-cache-dir -r requirements.txt

# Set up Gammu config
RUN echo "[gammu]\ndevice = /dev/ttyUSB3\nconnection = at" > /etc/gammurc

# Set permissions
RUN chmod +x entrypoint.sh

ENTRYPOINT ["./entrypoint.sh"]
