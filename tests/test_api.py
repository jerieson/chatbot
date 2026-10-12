import pytest
from fastapi.testclient import TestClient

from backend import main


class FakeService:
    class llm_fallback:
        enabled = False

    async def get_response(self, message, session_id, use_fallback):
        if message == "boom":
            raise RuntimeError("secret db password in traceback")
        return {
            "message": f"echo: {message}",
            "intent": "pokemon_type",
            "confidence": 0.9,
            "session_id": session_id or "new-session",
            "used_fallback": False,
            "fallback_reason": None,
        }


@pytest.fixture
def client(monkeypatch):
    async def noop():
        return None

    monkeypatch.setattr(main.Database, "init", noop)
    monkeypatch.setattr(main.Database, "close", noop)
    monkeypatch.setattr(main, "chat_service", FakeService())
    with TestClient(main.app) as c:
        yield c


def test_chat_returns_session_and_reuses_it(client):
    first = client.post("/chat", json={"message": "hi"}).json()
    assert first["session_id"] == "new-session"

    second = client.post("/chat", json={"message": "hi", "session_id": "abc"}).json()
    assert second["session_id"] == "abc"


def test_chat_rejects_blank_message(client):
    assert client.post("/chat", json={"message": "   "}).status_code == 400


def test_chat_hides_internal_errors(client):
    resp = client.post("/chat", json={"message": "boom"})
    assert resp.status_code == 500
    assert "secret" not in resp.text


def test_health_reports_readiness(client):
    body = client.get("/health").json()
    assert body["chatbot_ready"] is True
    assert body["llm_fallback_ready"] is False
