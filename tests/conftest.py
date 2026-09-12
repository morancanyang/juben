import os
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
test_path = ROOT / "runtime" / f"test-{uuid4().hex}.db"
os.environ["DATABASE_URL"] = f"sqlite:///{test_path.as_posix()}"
os.environ["APP_ENV"] = "test"
os.environ["PROVIDER"] = "mock"
os.environ["DELIVERY_DELAY"] = "0.02"

from api.db import engine
from api.main import app, rate_windows
from api.migrate import migrate
from api.models import Base


@pytest.fixture
def client():
    Base.metadata.drop_all(engine)
    migrate()
    rate_windows.clear()
    with TestClient(app) as client:
        yield client


@pytest.fixture
def player(client):
    res = client.post("/api/v1/auth/guest", json={})
    assert res.status_code == 200, res.text
    user = res.json()["user"]
    client.headers["X-CSRF-Token"] = user["csrf"]
    return client


def pytest_sessionfinish(session, exitstatus):
    engine.dispose()
    for suffix in ["", "-wal", "-shm"]:
        p = Path(str(test_path) + suffix)
        try:
            p.unlink(missing_ok=True)
        except PermissionError:
            pass
