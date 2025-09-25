# Use Python 3.11 with shared libraries (more stable than 3.13)
FROM python:3.11-slim

# Install system dependencies for PyInstaller and development
RUN apt-get update && apt-get install -y \
    python3-dev \
    build-essential \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt
RUN pip install --no-cache-dir pyinstaller gunicorn

# Copy the application code
COPY . .

# Create builds directory
RUN mkdir -p /app/builds

# Expose port
EXPOSE 5001

# Use gunicorn for production
CMD ["gunicorn", "--bind", "0.0.0.0:5001", "--timeout", "300", "server:app"]