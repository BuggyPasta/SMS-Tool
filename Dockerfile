# Use Debian Bookworm as base image
FROM debian:bookworm-slim

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    gammu \
    gammu-smsd \
    libgammu8 \
    libgammu-dev \
    libgammu-i18n \
    python3-gammu \
    gcc \
    pkg-config \
    tzdata \
    curl \
    gosu \
    && rm -rf /var/lib/apt/lists/*

# Set timezone to London
ENV TZ=Europe/London
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Create app directory and necessary subdirectories
WORKDIR /app

# Create directories and set permissions
RUN mkdir -p /app/database /app/logs /app/templates && \
    chmod 755 /app/database /app/logs /app/templates && \
    touch /app/logs/gammu.log && \
    chmod 666 /app/logs/gammu.log

# Create system user with dialout as primary group
RUN adduser --system --no-create-home --ingroup dialout gammuuser

# Set up Gammu configuration
RUN mkdir -p /etc/gammu && \
    mkdir -p /home/gammuuser/.config/gammu

# Copy application code
COPY . .

# Copy gammurc to both system and user locations
COPY docker/gammu/gammurc /etc/gammurc
COPY docker/gammu/gammurc /home/gammuuser/.config/gammu/config

# Set correct ownership and permissions for gammurc files
RUN chown root:dialout /etc/gammurc && \
    chmod 644 /etc/gammurc

# Set environment variable for XDG config
ENV XDG_CONFIG_HOME=/home/gammuuser/.config

# Save schema.sql as template in a different location
RUN cp /app/database/schema.sql /app/templates/schema.sql.template

# Create entrypoint script
RUN echo '#!/bin/bash' > /entrypoint.sh && \
    echo 'if [ ! -f /app/database/schema.sql ]; then' >> /entrypoint.sh && \
    echo '    cp /app/templates/schema.sql.template /app/database/schema.sql' >> /entrypoint.sh && \
    echo '    chmod 644 /app/database/schema.sql' >> /entrypoint.sh && \
    echo 'fi' >> /entrypoint.sh && \
    echo 'if [ -e /dev/ttyUSB3 ]; then' >> /entrypoint.sh && \
    echo '    chmod 660 /dev/ttyUSB3' >> /entrypoint.sh && \
    echo '    chown root:dialout /dev/ttyUSB3' >> /entrypoint.sh && \
    echo '    ls -l /dev/ttyUSB3' >> /entrypoint.sh && \
    echo '    id gammuuser' >> /entrypoint.sh && \
    echo '    groups gammuuser' >> /entrypoint.sh && \
    echo '    ls -l /etc/gammurc /home/gammuuser/.config/gammu/config' >> /entrypoint.sh && \
    echo 'fi' >> /entrypoint.sh && \
    echo 'chown -R gammuuser:dialout /app/database /app/logs /home/gammuuser/.config' >> /entrypoint.sh && \
    echo 'chmod -R 775 /app/database /app/logs /home/gammuuser/.config' >> /entrypoint.sh && \
    echo 'echo "Running preflight checks..."' >> /entrypoint.sh && \
    echo 'gosu gammuuser python3 /app/app/preflight.py' >> /entrypoint.sh && \
    echo 'if [ $? -ne 0 ]; then' >> /entrypoint.sh && \
    echo '    echo "Preflight checks failed. Please check the logs above."' >> /entrypoint.sh && \
    echo '    exit 1' >> /entrypoint.sh && \
    echo 'fi' >> /entrypoint.sh && \
    echo 'exec gosu gammuuser "$@"' >> /entrypoint.sh && \
    chmod +x /entrypoint.sh

# Create and activate virtual environment
RUN python3 -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH"

# Install Python dependencies in virtual environment
RUN . /app/venv/bin/activate && pip install --no-cache-dir -r requirements.txt

# Set permissions for app directory and config
RUN chown -R gammuuser:dialout /app /home/gammuuser/.config && \
    chmod -R 755 /app /home/gammuuser/.config

# Expose port
EXPOSE 4001

# Set the entrypoint
ENTRYPOINT ["/entrypoint.sh"]

# Run the application using the virtual environment's Python
CMD ["/app/venv/bin/python", "-m", "flask", "run", "--host=0.0.0.0", "--port=4001"] 