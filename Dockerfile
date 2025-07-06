FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for Chromium
RUN apt-get update && apt-get install -y \
    wget curl gnupg unzip fonts-liberation libnss3 libatk-bridge2.0-0 \
    libxss1 libgtk-3-0 libasound2 libxshmfence1 libgbm1 libxdamage1 \
    libxcomposite1 libxrandr2 libxinerama1 libxext6 libx11-xcb1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN python -m playwright install chromium

COPY . .

EXPOSE 8080
CMD ["python", "resolve_server.py"]
