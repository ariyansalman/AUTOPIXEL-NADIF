#!/bin/sh
set -eu

echo "[startup] Container entrypoint started"
echo "[startup] DISPLAY=${DISPLAY:-not-set}"

echo "[startup] Chromium: $(chromium --version 2>&1 || true)"
echo "[startup] ChromeDriver: $(chromedriver --version 2>&1 || true)"
echo "[startup] xauth: $(xauth -V 2>&1 || true)"

echo "[startup] TELEGRAM_BOT_TOKEN: $([ -n "${TELEGRAM_BOT_TOKEN:-}" ] && echo set || echo MISSING)"

echo "[startup] Starting Xvfb and bot..."

exec xvfb-run --auto-servernum --server-args="-screen 0 1280x900x24" python -u main.py
