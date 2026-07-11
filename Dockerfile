# Playwright ve Chromium zaten hazır!
FROM mcr.microsoft.com/playwright:python

WORKDIR /app

# Önce bağımlılıkları kopyala (cache için)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Uygulama dosyalarını kopyala
COPY main.py .
COPY accounts.txt .

# Uygulamayı başlat
CMD ["python", "main.py"]
