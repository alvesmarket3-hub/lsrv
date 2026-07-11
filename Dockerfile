FROM python:3.10-slim

WORKDIR /app

# Sistem bağımlılıklarını yükle (Playwright Linux'ta bunlara ihtiyaç duyar)
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Önce bağımlılıkları kopyala ve kur
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Playwright'un tarayıcısını ve tüm sistem bağımlılıklarını indir (BU ÇOK ÖNEMLİ)
RUN playwright install chromium
RUN playwright install-deps

# Uygulama dosyalarını kopyala
COPY main.py .
COPY accounts.txt .

CMD ["python", "main.py"]
