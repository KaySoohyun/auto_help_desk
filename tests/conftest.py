import os
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Aislar la config antes de importar la app: usar una DB de test en /tmp
TEST_DB = f"sqlite:///{Path('/tmp/opencode') / 'test_auth.db'}"

os.environ["DATABASE_URL"] = TEST_DB

from app.core.config import settings  # noqa: E402
from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as test_client:
        yield test_client
    Base.metadata.drop_all(bind=engine)
