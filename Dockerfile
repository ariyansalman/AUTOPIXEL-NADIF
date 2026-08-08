FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    CHROME_BIN=/usr/bin/chromium \
    CHROMEDRIVER_PATH=/usr/bin/chromedriver \
    SE_OFFLINE=true \
    DISPLAY=:99

# Chromium + matching Debian chromedriver + Xvfb for Railway's Linux container.
# xauth is required by xvfb-run when it creates the temporary X authority file.
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    chromium-driver \
    xvfb \
    xauth \
    ca-certificates \
    fonts-liberation \
    fonts-noto-cjk \
    fonts-noto-color-emoji \
    libnss3 \
    libgbm1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN python -m pip install --upgrade pip setuptools wheel \
    && python -m pip install -r requirements.txt

COPY . .

RUN chromium --version \
    && chromedriver --version \
    && xauth -V \
    && xvfb-run --help >/dev/null \
    && python -c "import telegram, selenium, undetected_chromedriver, pyotp; print('Python dependencies OK')"

# Run the bot inside a virtual X display so headless=False is usable on Railway.
CMD ["xvfb-run", "--auto-servernum", "--server-args=-screen 0 1280x900x24", "python", "main.py"]
