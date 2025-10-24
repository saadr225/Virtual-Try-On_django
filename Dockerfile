# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# Add production optimization
ENV PYTHONOPTIMIZE=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies with production optimizations
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install gunicorn  # Add production server

# Copy project files
COPY VTON_APP/ ./VTON_APP/
COPY .env.example .env.example

# # Create media directories
# RUN mkdir -p VTON_APP/media/uploads VTON_APP/media/output VTON_APP/media/temp

# Expose port
EXPOSE 8080

# Set working directory to Django project
WORKDIR /app/VTON_APP

# Run migrations and start server
# Copy startup script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]