#!/bin/sh
set -u

log() {
  echo "[startup] $1"
}

log "Container entrypoint started"
log "DISPLAY=${DISPLAY:-not-set}"
log "Chromium: $(chromium --version 2>&1 || true)"
log "ChromeDriver: $(chromedriver --version 2>&1 || true)"
log "xauth: $(xauth -V 2>&1 || true)"
log "Xvfb: $(Xvfb -version 2>&1 | head -n 1 || true)"
log "TELEGRAM_BOT_TOKEN: $([ -n "${TELEGRAM_BOT_TOKEN:-}" ] && echo set || echo MISSING)"

# Start Xvfb directly instead of wrapping Python with xvfb-run.
# This avoids xvfb-run/xauth startup issues and makes the real Python
# process and its exit status visible in Railway logs.
export DISPLAY=:99
log "Starting Xvfb on ${DISPLAY}..."
Xvfb :99 -screen 0 1280x900x24 -ac >/tmp/xvfb.log 2>&1 &
XVFB_PID=$!

sleep 1
if ! kill -0 "$XVFB_PID" 2>/dev/null; then
  log "ERROR: Xvfb failed to start"
  cat /tmp/xvfb.log 2>/dev/null || true
  exit 1
fi

log "Xvfb started (PID ${XVFB_PID})"
log "Starting Python bot..."

python -u main.py
EXIT_CODE=$?

log "Python bot exited with code ${EXIT_CODE}"
log "--- Xvfb log ---"
cat /tmp/xvfb.log 2>/dev/null || true
exit "$EXIT_CODE"
