"""Pytest fixtures."""

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("OPENAI_API_KEY", "test-openai")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic")
os.environ.setdefault("GOOGLE_API_KEY", "test-google")
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ.setdefault("ALLOW_PUBLIC_REGISTRATION", "true")
os.environ.setdefault("ADMIN_API_KEY", "test-admin-key")
os.environ.setdefault("AUTH_DEV_MODE", "true")
os.environ.setdefault("ENCRYPTION_KEY", "test-encryption-key-32-characters!")
os.environ.setdefault("SECRET_KEY", "test-jwt-secret-key-please-change")

from app.core.config import get_settings
from app.db import base as db_base
from app.db.base import Base, get_db
from app.main import create_app


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def db_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    db_base.engine = engine
    db_base.SessionLocal = sessionmaker(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(db_engine):
    session = db_base.SessionLocal()
    yield session
    session.close()


@pytest.fixture
def client(db_engine):
    TestingSession = sessionmaker(bind=db_engine)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def auth_login(client):
    """Return a helper that logs in via AUTH_DEV_MODE and yields auth headers + user."""

    def _login(email: str = "user@example.com", name: str = "User"):
        resp = client.post(
            "/api/v1/auth/dev-login",
            json={"email": email, "name": name},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        headers = {"Authorization": f"Bearer {data['access_token']}"}
        return headers, data["user"]

    return _login
