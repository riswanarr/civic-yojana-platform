from fastapi.testclient import TestClient

from app.api import chatbot
from app.api import sync
from app.main import app
from app.services.chatbot_service import (
    GEMINI_QUOTA_UNAVAILABLE_RESPONSE,
    GeminiQuotaExceededError,
)


def test_openapi_schema_available():
    client = TestClient(app)
    response = client.get("/openapi.json")

    assert response.status_code == 200


def test_chatbot_returns_503_when_gemini_quota_is_unavailable(monkeypatch):
    def raise_quota_error(question: str):
        raise GeminiQuotaExceededError

    monkeypatch.setattr(chatbot.chatbot_service, "answer_question", raise_quota_error)

    client = TestClient(app)
    response = client.post("/api/v1/chatbot", json={"question": "Which schemes can help me?"})

    assert response.status_code == 503
    assert response.json() == GEMINI_QUOTA_UNAVAILABLE_RESPONSE


def test_sync_endpoint_returns_sync_summary(monkeypatch):
    expected = {
        "sources_checked": 2,
        "new_opportunities": 3,
        "updated_opportunities": 1,
        "notifications_created": 4,
    }

    monkeypatch.setattr(sync.update_service, "run_sync", lambda: expected)

    client = TestClient(app)
    response = client.post("/api/v1/sync")

    assert response.status_code == 200
    assert response.json() == expected
