"""Encrypted provider credential management."""

from datetime import datetime

from sqlalchemy.orm import Session

from app.core.exceptions import AppError, AuthError
from app.core.security import decrypt_secret, encrypt_secret, mask_api_key
from app.models.models import User, UserPreferences, UserProviderCredential
from app.providers import PROVIDER_MODELS, SUPPORTED_PROVIDERS, get_provider, list_provider_catalog


def list_credentials(db: Session, user: User) -> list[dict]:
    rows = (
        db.query(UserProviderCredential)
        .filter(UserProviderCredential.user_id == user.id)
        .all()
    )
    result = []
    for row in rows:
        try:
            masked = mask_api_key(decrypt_secret(row.encrypted_api_key))
        except AppError:
            masked = f"****{row.key_hint}"
        result.append(
            {
                "provider": row.provider,
                "configured": True,
                "masked_key": masked,
                "key_hint": row.key_hint,
                "is_valid": row.is_valid,
                "last_validated_at": row.last_validated_at.isoformat() if row.last_validated_at else None,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            }
        )
    return result


def get_decrypted_key(db: Session, user: User, provider: str, *, require_valid: bool = True) -> str:
    row = (
        db.query(UserProviderCredential)
        .filter(
            UserProviderCredential.user_id == user.id,
            UserProviderCredential.provider == provider,
        )
        .first()
    )
    if not row:
        raise AppError(
            f"No {provider} API key configured. Add one in Settings.",
            status_code=400,
        )
    if require_valid and not row.is_valid:
        raise AppError(
            f"Your {provider} API key is marked invalid. Update it in Settings.",
            status_code=400,
        )
    return decrypt_secret(row.encrypted_api_key)


async def upsert_credential(db: Session, user: User, provider: str, api_key: str) -> dict:
    if provider not in SUPPORTED_PROVIDERS:
        raise AppError(f"Unsupported provider: {provider}", status_code=400)
    if not api_key or len(api_key.strip()) < 8:
        raise AppError("API key looks invalid.", status_code=400)

    api_key = api_key.strip()
    provider_impl = get_provider(provider)
    is_valid = await provider_impl.validate_key(api_key)

    row = (
        db.query(UserProviderCredential)
        .filter(
            UserProviderCredential.user_id == user.id,
            UserProviderCredential.provider == provider,
        )
        .first()
    )
    hint = api_key[-4:]
    encrypted = encrypt_secret(api_key)
    now = datetime.utcnow()
    if row:
        row.encrypted_api_key = encrypted
        row.key_hint = hint
        row.is_valid = is_valid
        row.last_validated_at = now if is_valid else row.last_validated_at
        row.updated_at = now
    else:
        row = UserProviderCredential(
            user_id=user.id,
            provider=provider,
            encrypted_api_key=encrypted,
            key_hint=hint,
            is_valid=is_valid,
            last_validated_at=now if is_valid else None,
        )
        db.add(row)
    db.commit()

    prefs = db.query(UserPreferences).filter(UserPreferences.user_id == user.id).first()
    if prefs and not prefs.default_provider:
        prefs.default_provider = provider
        prefs.default_model = PROVIDER_MODELS[provider][0]["id"]
        db.commit()

    return {
        "provider": provider,
        "configured": True,
        "masked_key": mask_api_key(api_key),
        "is_valid": is_valid,
        "message": "Key saved." if is_valid else "Key saved but validation failed.",
    }


async def test_credential(db: Session, user: User, provider: str, api_key: str | None = None) -> dict:
    if provider not in SUPPORTED_PROVIDERS:
        raise AppError(f"Unsupported provider: {provider}", status_code=400)
    key = api_key.strip() if api_key else get_decrypted_key(db, user, provider)
    ok = await get_provider(provider).validate_key(key)
    if api_key is None:
        row = (
            db.query(UserProviderCredential)
            .filter(
                UserProviderCredential.user_id == user.id,
                UserProviderCredential.provider == provider,
            )
            .first()
        )
        if row:
            row.is_valid = ok
            row.last_validated_at = datetime.utcnow()
            db.commit()
    return {"provider": provider, "is_valid": ok}


def delete_credential(db: Session, user: User, provider: str) -> None:
    row = (
        db.query(UserProviderCredential)
        .filter(
            UserProviderCredential.user_id == user.id,
            UserProviderCredential.provider == provider,
        )
        .first()
    )
    if not row:
        raise AppError("Credential not found.", status_code=404)
    db.delete(row)
    db.commit()


def get_preferences(db: Session, user: User) -> dict:
    prefs = db.query(UserPreferences).filter(UserPreferences.user_id == user.id).first()
    if not prefs:
        prefs = UserPreferences(user_id=user.id)
        db.add(prefs)
        db.commit()
        db.refresh(prefs)
    configured = {
        c.provider
        for c in db.query(UserProviderCredential)
        .filter(UserProviderCredential.user_id == user.id)
        .all()
    }
    return {
        "default_provider": prefs.default_provider,
        "default_model": prefs.default_model,
        "allow_fallback": prefs.allow_fallback,
        "configured_providers": sorted(configured),
        "catalog": [
            {
                **entry,
                "configured": entry["id"] in configured,
            }
            for entry in list_provider_catalog()
        ],
    }


def update_preferences(
    db: Session,
    user: User,
    default_provider: str | None,
    default_model: str | None,
    allow_fallback: bool | None,
) -> dict:
    prefs = db.query(UserPreferences).filter(UserPreferences.user_id == user.id).first()
    if not prefs:
        prefs = UserPreferences(user_id=user.id)
        db.add(prefs)

    if default_provider is not None:
        if default_provider and default_provider not in SUPPORTED_PROVIDERS:
            raise AppError("Unsupported provider.", status_code=400)
        # Ensure user owns a key for that provider
        if default_provider:
            owns = (
                db.query(UserProviderCredential)
                .filter(
                    UserProviderCredential.user_id == user.id,
                    UserProviderCredential.provider == default_provider,
                )
                .first()
            )
            if not owns:
                raise AppError(
                    f"Add a {default_provider} API key before setting it as default.",
                    status_code=400,
                )
            if default_model and default_model not in [
                m["id"] for m in PROVIDER_MODELS[default_provider]
            ]:
                raise AppError("Unsupported model for provider.", status_code=400)
        prefs.default_provider = default_provider
        if default_model is not None:
            prefs.default_model = default_model

    if allow_fallback is not None:
        prefs.allow_fallback = allow_fallback

    db.commit()
    return get_preferences(db, user)


def resolve_provider_model(
    db: Session,
    user: User,
    provider: str | None,
    model: str | None,
) -> tuple[str, str, str]:
    """Return (provider, model, decrypted_api_key) with ownership checks.

    Does not silently fall back unless the user enabled allow_fallback.
    """
    prefs = get_preferences(db, user)
    allow_fallback = bool(prefs.get("allow_fallback"))
    chosen_provider = provider or prefs.get("default_provider")
    chosen_model = model or prefs.get("default_model")

    if not chosen_provider:
        raise AppError(
            "No AI provider selected. Add an API key in Settings and choose a default model.",
            status_code=400,
        )
    if chosen_provider not in SUPPORTED_PROVIDERS:
        raise AppError("Unsupported provider.", status_code=400)

    models = [m["id"] for m in PROVIDER_MODELS[chosen_provider]]
    if not chosen_model:
        chosen_model = models[0]
    if chosen_model not in models:
        raise AppError("Unsupported model for provider.", status_code=400)

    try:
        api_key = get_decrypted_key(db, user, chosen_provider, require_valid=True)
        return chosen_provider, chosen_model, api_key
    except AppError as primary_error:
        if not allow_fallback:
            raise
        # Explicit user opt-in: try other configured valid providers
        for alt in SUPPORTED_PROVIDERS:
            if alt == chosen_provider:
                continue
            try:
                api_key = get_decrypted_key(db, user, alt, require_valid=True)
                alt_model = PROVIDER_MODELS[alt][0]["id"]
                return alt, alt_model, api_key
            except AppError:
                continue
        raise primary_error
