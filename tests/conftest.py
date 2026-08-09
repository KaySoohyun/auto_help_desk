import os
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Aislar la config antes de importar la app: usar una DB de test en /tmp
TEST_DB_DIR = Path("/tmp/opencode")
TEST_DB_DIR.mkdir(parents=True, exist_ok=True)
TEST_DB = f"sqlite:///{TEST_DB_DIR / 'test_auth.db'}"

os.environ["DATABASE_URL"] = TEST_DB

from app.core.config import settings  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models.user import User  # noqa: E402

# El registro público (/auth/register) solo permite roles no admin (seguridad).
PUBLIC_REGISTRATION_ROLES = {"agent", "supervisor"}


@pytest.fixture(autouse=True)
def clean_db() -> Generator[None, None, None]:
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client


def register_login(client: TestClient, email: str, role: str, tenant_id: str | None = None) -> dict:
    password = "segura-123"
    if role in PUBLIC_REGISTRATION_ROLES:
        client.post(
            "/auth/register",
            json={"email": email, "password": password, "role": role, "tenant_id": tenant_id},
        )
    else:
        with SessionLocal() as db:
            db.add(
                User(
                    email=email,
                    password_hash=hash_password(password),
                    role=role,
                    tenant_id=tenant_id,
                    is_active=True,
                )
            )
            db.commit()
    login = client.post("/auth/login", json={"email": email, "password": password})
    return login.json()