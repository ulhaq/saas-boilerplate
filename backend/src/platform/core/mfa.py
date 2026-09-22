"""TOTP two-factor authentication primitives (RFC 6238).

Secrets are stored Fernet-encrypted with a key derived from APP_SECRET, so a
database dump alone cannot mint codes. Rotating APP_SECRET invalidates every
enrolled authenticator (as it does every signed token). Recovery codes are
high-entropy one-time values, stored as keyed SHA-256 hashes - argon2 would
make checking ten candidates per login needlessly slow.
"""

import base64
import hashlib
import hmac
import secrets
import time

import pyotp
from cryptography.fernet import Fernet, InvalidToken

from src.platform.core.config import settings
from src.platform.models.user import User

# Codes from the previous/next 30s step are accepted to absorb clock drift.
_VALID_WINDOW = 1
_RECOVERY_CODE_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"


def _key(purpose: bytes) -> bytes:
    return hashlib.sha256(
        purpose + settings.app_secret.get_secret_value().encode()
    ).digest()


def _fernet() -> Fernet:
    return Fernet(base64.urlsafe_b64encode(_key(b"mfa-secret:")))


def mfa_required(user: User) -> bool:
    """Whether this user must present a second factor (feature on + enrolled)."""
    return settings.mfa_enabled and user.mfa_active


def generate_secret() -> str:
    return pyotp.random_base32()


def encrypt_secret(secret: str) -> str:
    return _fernet().encrypt(secret.encode()).decode()


def decrypt_secret(encrypted: str) -> str | None:
    try:
        return _fernet().decrypt(encrypted.encode()).decode()
    except InvalidToken:
        return None


def provisioning_uri(secret: str, email: str) -> str:
    return pyotp.TOTP(secret).provisioning_uri(
        name=email, issuer_name=settings.app_name
    )


def _normalize(code: str) -> str:
    return "".join(code.split()).replace("-", "").lower()


def verify_totp(secret: str, code: str, last_used_step: int | None) -> int | None:
    """Return the matched time step, or None if the code is invalid or was
    already used (step <= last_used_step)."""
    code = _normalize(code)
    if len(code) != 6 or not code.isdigit():
        return None
    totp = pyotp.TOTP(secret)
    now_step = int(time.time()) // totp.interval
    for step in range(now_step - _VALID_WINDOW, now_step + _VALID_WINDOW + 1):
        if last_used_step is not None and step <= last_used_step:
            continue
        if hmac.compare_digest(totp.generate_otp(step), code):
            return step
    return None


def generate_recovery_codes(count: int | None = None) -> list[str]:
    """Plain codes formatted as xxxxx-xxxxx; shown to the user exactly once."""
    codes = []
    for _ in range(count or settings.mfa_recovery_code_count):
        raw = "".join(secrets.choice(_RECOVERY_CODE_ALPHABET) for _ in range(10))
        codes.append(f"{raw[:5]}-{raw[5:]}")
    return codes


def hash_recovery_code(code: str) -> str:
    return hmac.new(
        _key(b"mfa-recovery:"), _normalize(code).encode(), hashlib.sha256
    ).hexdigest()


def match_recovery_code(code: str, hashes: list[str] | None) -> str | None:
    """Return the stored hash that matches `code`, or None."""
    candidate = hash_recovery_code(code)
    for stored in hashes or []:
        if hmac.compare_digest(stored, candidate):
            return stored
    return None
