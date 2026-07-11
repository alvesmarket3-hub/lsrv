FROM mcr.microsoft.com/playwright:python-3.12

WORKDIR /app

# Sistem bağımlılıkları zaten base imajda hazır, sadece Python paketlerini yükle
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Base imajda Chromium hazır ama rebrowser için tekrar kurmaya gerek yok,
# yine de emin olmak için çalıştıralım (kısa sürer)
RUN playwright install chromium

COPY . .

CMD ["python", "main.py"]
