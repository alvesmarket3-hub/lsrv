FROM python:3.10-slim

WORKDIR /app

# Sistem bağımlılıklarını yükle (Playwright için zorunlu)
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Önce requirements.txt'yi kopyala ve pip ile kur
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Playwright tarayıcısını ve bağımlılıklarını indir (BU ADIM ÇOK ÖNEMLİ)
RUN playwright install chromium
RUN playwright install-deps

# Uygulama dosyalarını kopyala
COPY main.py .
COPY accounts.txt .

# -u ile çalıştır ki loglar anında görünsün
CMD ["python", "-u", "main.py"]
