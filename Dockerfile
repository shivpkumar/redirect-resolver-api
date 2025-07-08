FROM python:3.10-slim

WORKDIR /app

# Install system dependencies (if needed for Playwright or other resolvers)
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    libnss3 \
    libxss1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    libx11-xcb1 \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Copy app files
COPY . .

# Install Python dependencies (including bs4)
RUN pip install --no-cache-dir -r requirements.txt

# Start server
CMD ["python", "resolve_server.py"]
