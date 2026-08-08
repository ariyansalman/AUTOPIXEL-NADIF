"""Compatibility layer for common Google Authenticator secret formats.

Google can expose a TOTP secret as a plain Base32 value, a value containing
spaces/hyphens, or an otpauth:// URI. PyOTP expects the Base32 secret itself.
This module normalizes those legitimate formats before the existing bot calls
pyotp.TOTP(secret).
"""

from __future__ import annotations

import base64
import re
from urllib.parse import parse_qs, urlparse

import pyotp

_ORIGINAL_TOTP = pyotp.TOTP
_BASE32_RE = re.compile(r"^[A-Z2-7]+=*$")


def normalize_totp_secret(value: str) -> str:
    """Return a canonical Base32 TOTP secret from common input formats."""
    secret = str(value or "").strip()
    if not secret:
        raise ValueError("TOTP secret is empty")

    # Accept otpauth://totp/...?...secret=BASE32 URIs copied from authenticators.
    if secret.lower().startswith("otpauth://"):
        parsed = urlparse(secret)
        query = parse_qs(parsed.query)
        candidates = query.get("secret") or []
        if not candidates:
            raise ValueError("otpauth URI does not contain a secret")
        secret = candidates[0]

    # Users commonly copy Base32 values with spaces or hyphens for readability.
    secret = re.sub(r"[\s-]+", "", secret).upper()
    secret = secret.rstrip("=")

    if not _BASE32_RE.fullmatch(secret):
        raise ValueError(
            "TOTP secret contains characters outside the Base32 alphabet (A-Z, 2-7)"
        )

    # Validate before PyOTP receives it so errors are clear and deterministic.
    try:
        base64.b32decode(secret + "=" * ((8 - len(secret) % 8) % 8), casefold=True)
    except Exception as exc:
        raise ValueError("TOTP secret is not valid Base32") from exc

    return secret


def _compatible_totp(secret: str, *args, **kwargs):
    """Construct the normal PyOTP TOTP object with a normalized secret."""
    return _ORIGINAL_TOTP(normalize_totp_secret(secret), *args, **kwargs)


# The existing offer handler already imports pyotp locally and calls
# pyotp.TOTP(secret). Keeping this tiny compatibility patch avoids changing
# that handler's business flow while accepting standard secret formats.
pyotp.TOTP = _compatible_totp
