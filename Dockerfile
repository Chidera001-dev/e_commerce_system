# Use official Python image
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file first (for caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy the entire project
COPY . .

#  ensure the Celery entrypoint can find the Django project
ENV PYTHONPATH=/app

# Expose port 8000 for Django
EXPOSE 8000

# Default command — can be overridden in docker-compose
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]



