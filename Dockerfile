# Use official lightweight Python image
FROM python:3.11-slim

# Set environment variables to prevent Python buffering and write operations
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system libraries required for Pillow, ReportLab font rendering, and crypto compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libfreetype6-dev \
    libjpeg62-turbo-dev \
    zlib1g-dev \
    libpng-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency definition first for caching layer
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# CRITICAL SECURITY RULE: Ensure private key is NOT copied if accidentally left in directory
RUN rm -f private_key.pem generate_trial_keys.py

# Expose Streamlit default port
EXPOSE 8501

# Streamlit healthcheck
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Launch Streamlit with CORS disabled for local preview iframes
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.enableCORS=false"]