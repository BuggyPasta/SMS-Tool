# Use Alpine Linux as base image
FROM alpine:3.19

# Install system dependencies
RUN apk add --no-cache \
    python3 \
    py3-pip \
    python3-dev \
    gammu \
    gammu-dev \
    gcc \
    musl-dev \
    linux-headers \
    pkgconfig \
    tzdata

# Set timezone to London
ENV TZ=Europe/London
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Create app directory and necessary subdirectories
WORKDIR /app

# Create directories
RUN mkdir -p /app/database /app/logs /app/templates

# Copy application code
COPY . .

# Save schema.sql as template in a different location
RUN cp /app/database/schema.sql /app/templates/schema.sql.template

# Create entrypoint script
RUN echo '#!/bin/sh' > /entrypoint.sh && \
    echo 'if [ ! -f /app/database/schema.sql ]; then' >> /entrypoint.sh && \
    echo '    cp /app/templates/schema.sql.template /app/database/schema.sql' >> /entrypoint.sh && \
    echo '    chmod 644 /app/database/schema.sql' >> /entrypoint.sh && \
    echo 'fi' >> /entrypoint.sh && \
    echo 'exec "$@"' >> /entrypoint.sh && \
    chmod +x /entrypoint.sh

# Create and activate virtual environment
RUN python3 -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH"

# Install Python dependencies in virtual environment
RUN . /app/venv/bin/activate && pip install --no-cache-dir -r requirements.txt

# Set permissions
RUN chmod -R 755 /app

# Expose port
EXPOSE 4001

# Set the entrypoint
ENTRYPOINT ["/entrypoint.sh"]

# Run the application using the virtual environment's Python
CMD ["/app/venv/bin/python", "-m", "flask", "run", "--host=0.0.0.0", "--port=4001"] 