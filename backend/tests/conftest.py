import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def settings(tmp_path):
    return Settings.for_testing(tmp_path)


@pytest.fixture
def client(settings):
    with TestClient(create_app(settings)) as c:
        yield c


def make_project(client, **kw):
    body = {"title": "Rainbow", "prompt": "How do rainbows form?", **kw}
    r = client.post("/projects", json=body)
    assert r.status_code == 201, r.text
    return r.json()


def run_story(client, pid, **kw):
    body = {"prompt": "How do rainbows form?", "duration_seconds": 60, **kw}
    r = client.post(f"/projects/{pid}/story", json=body)
    assert r.status_code == 202, r.text
    return r.json()
