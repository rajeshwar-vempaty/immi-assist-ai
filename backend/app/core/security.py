"""API key hashing and generation."""

import hashlib
import secrets


def hash_api_key(api_key: str) -> str:
    """Return SHA-256 hex digest of an API key."""
    return hashlib.sha256(api_key.encode()).hexdigest()


def generate_api_key() -> str:
    """Generate a new API key with immi_ prefix."""
    return f"immi_{secrets.token_urlsafe(32)}"
