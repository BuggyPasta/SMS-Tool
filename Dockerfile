# Use Alpine Linux as base image
FROM alpine:3.19

# Install system dependencies
RUN apk add --no-cache \
    python3 \
    py3-pip \
    python3-dev \
    gammu \
    tzdata

# Set timezone to London
ENV TZ=Europe/London
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Create app directory
WORKDIR /app

# Create and activate virtual environment
RUN python3 -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH"

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies in virtual environment
RUN . /app/venv/bin/activate && pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/database /app/logs

# Set permissions
RUN chmod -R 755 /app

# Expose port
EXPOSE 4001

# Run the application using the virtual environment's Python
CMD ["/app/venv/bin/python", "-m", "flask", "run", "--host=0.0.0.0", "--port=4001"] 