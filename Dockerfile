# Doğru adres: eğik çizgi (/) kullanımına dikkat edin!
FROM mcr.microsoft.com/playwright/python:latest

WORKDIR /app

# Bağımlılıkları kopyala ve kur
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Uygulama dosyalarını kopyala
COPY main.py .
COPY accounts.txt .

# Uygulamayı başlat
CMD ["python", "main.py"]
