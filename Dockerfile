FROM python:3.10-slim

WORKDIR /app

# Playwright için gerekli tüm sistem paketlerini manuel yükle
RUN apt-get update && apt-get install -y \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libxrender1 \
    libxss1 \
    libxtst6 \
    libgbm1 \
    libgtk-3-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    libpango-1.0-0 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libnss3 \
    libasound2 \
    libglib2.0-0 \
    libgdk-pixbuf2.0-0 \
    libnotify4 \
    libxcb1 \
    libxcb-shm0 \
    libxcb-xfixes0 \
    libxcb-shape0 \
    libxcb-randr0 \
    libxcb-keysyms1 \
    libxcb-icccm4 \
    libxcb-xinerama0 \
    libxcb-xinput0 \
    libxcb-xkb1 \
    libxkbcommon-x11-0 \
    libxkbregistry0 \
    libfontconfig1 \
    libfreetype6 \
    libjpeg62-turbo \
    libpng16-16 \
    libwebp7 \
    libwebpdemux2 \
    libwebpmux3 \
    libvpx7 \
    libenchant-2-2 \
    libicu72 \
    libgstreamer1.0-0 \
    libgstreamer-plugins-base1.0-0 \
    libavcodec-extra58 \
    libavformat58 \
    libavutil56 \
    libavfilter7 \
    libavdevice58 \
    ffmpeg \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Python kütüphanesini yükle
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Chromium'u indir
RUN playwright install chromium

# Uygulama dosyaları
COPY main.py .
COPY accounts.txt .

# Xvfb ile çalıştır (sanal ekran)
CMD ["xvfb-run", "-a", "python", "-u", "main.py"]
