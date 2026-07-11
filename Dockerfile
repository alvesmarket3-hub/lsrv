FROM python:3.10-slim

# Playwright bağımlılıkları
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Playwright kurulumu
RUN pip install playwright==1.40.0 && \
    playwright install chromium && \
    playwright install-deps

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .
COPY accounts.txt .

CMD ["python", "main.py"]
