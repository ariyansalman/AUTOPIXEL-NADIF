FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    CHROME_BIN=/usr/bin/chromium \
    CHROMEDRIVER_PATH=/usr/bin/chromedriver \
    SE_OFFLINE=true

# Chromium + matching Debian chromedriver + runtime libraries needed by headless Chrome.
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    chromium-driver \
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

# Install Python dependencies first so source changes do not invalidate this layer.
COPY requirements.txt ./
RUN python -m pip install --upgrade pip setuptools wheel \
    && python -m pip install -r requirements.txt

# Copy the complete repository. This avoids accidentally omitting assets or
# runtime modules when the project structure changes.
COPY . .

# Verify the browser and driver exist before Railway starts the service.
RUN chromium --version \
    && chromedriver --version \
    && python -c "import telegram, selenium, undetected_chromedriver, pyotp; print('Python dependencies OK')"

CMD ["python", "main.py"]
