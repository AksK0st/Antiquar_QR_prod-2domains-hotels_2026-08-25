from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

import middleware.http as http_middleware
from middleware.http import ApplicationHttpMiddleware


def _client(monkeypatch):
    monkeypatch.setattr(
        http_middleware,
        "settings",
        SimpleNamespace(
            is_production=True,
            public_origins=[
                "https://gallery.real-museum.ru",
                "https://second.real-museum.ru",
            ],
        ),
    )
    app = FastAPI()
    app.add_middleware(ApplicationHttpMiddleware)

    @app.post("/api/admin/test")
    async def admin_test():
        return {"ok": True}

    return TestClient(app)


def test_admin_csrf_accepts_each_configured_domain(monkeypatch) -> None:
    client = _client(monkeypatch)

    for origin in (
        "https://gallery.real-museum.ru",
        "https://second.real-museum.ru",
    ):
        response = client.post("/api/admin/test", headers={"Origin": origin})
        assert response.status_code == 200


def test_admin_csrf_rejects_unknown_domain(monkeypatch) -> None:
    client = _client(monkeypatch)
    response = client.post(
        "/api/admin/test",
        headers={"Origin": "https://attacker.example-attacker.ru"},
    )
    assert response.status_code == 403


def test_admin_csrf_accepts_referer_from_secondary_domain(monkeypatch) -> None:
    client = _client(monkeypatch)
    response = client.post(
        "/api/admin/test",
        headers={"Referer": "https://second.real-museum.ru/admin/items/1"},
    )
    assert response.status_code == 200
