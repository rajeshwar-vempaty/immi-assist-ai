"""Authentication cryptography: hashing, JWT, Fernet encryption for provider keys."""

import base64
import hashlib
import logging
import secrets
from datetime import datetime, timedelta
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from jose import JWTError, jwt

from app.core.config import get_settings
from app.core.exceptions import AppError, AuthError

logger = logging.getLogger(__name__)


def hash_api_key(api_key: str) -> str:
    """Return SHA-256 hex digest of an API key."""
    return hashlib.sha256(api_key.encode()).hexdigest()


def generate_api_key() -> str:
    """Generate a new platform API key with immi_ prefix."""
    return f"immi_{secrets.token_urlsafe(32)}"


def mask_api_key(api_key: str) -> str:
    """Return a display-safe masked key like sk-****abcd."""
    if not api_key:
        return ""
    if len(api_key) <= 8:
        return "****"
    return f"{api_key[:3]}****{api_key[-4:]}"


def _fernet() -> Fernet:
    settings = get_settings()
    raw = settings.encryption_key or settings.secret_key
    digest = hashlib.sha256(raw.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(plaintext: str) -> str:
    """Encrypt a secret for database storage."""
    try:
        return _fernet().encrypt(plaintext.encode()).decode()
    except Exception as exc:
        logger.error("Encryption failure")
        raise AppError("Failed to encrypt credential.", status_code=500) from exc


def decrypt_secret(ciphertext: str) -> str:
    """Decrypt a secret from database storage."""
    try:
        return _fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken as exc:
        logger.error("Decryption failure: invalid token")
        raise AppError("Failed to decrypt credential.", status_code=500) from exc
    except Exception as exc:
        logger.error("Decryption failure")
        raise AppError("Failed to decrypt credential.", status_code=500) from exc


def create_access_token(user_id: str, extra: dict[str, Any] | None = None) -> str:
    settings = get_settings()
    payload = {
        "sub": user_id,
        "type": "access",
        "exp": datetime.utcnow() + timedelta(hours=settings.jwt_expire_hours),
        "iat": datetime.utcnow(),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        if payload.get("type") != "access" or not payload.get("sub"):
            raise AuthError("Invalid session token.", status_code=401)
        return payload
    except JWTError as exc:
        raise AuthError("Session expired or invalid. Please sign in again.", status_code=401) from exc
