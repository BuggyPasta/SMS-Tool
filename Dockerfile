# Use Alpine Linux as base image
FROM alpine:3.19

# Install system dependencies
RUN apk add --no-cache \
    python3 \
    py3-pip \
    gammu \
    tzdata

# Set timezone to London
ENV TZ=Europe/London
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Create app directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/database /app/logs

# Set permissions
RUN chmod -R 755 /app

# Expose port
EXPOSE 4001

# Run the application
CMD ["python3", "-m", "flask", "run", "--host=0.0.0.0", "--port=4001"] 