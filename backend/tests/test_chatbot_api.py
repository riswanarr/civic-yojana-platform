from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from app.api import chatbot
from app.main import app


AUTH_HEADERS = {"Authorization": "Bearer test-token"}


def test_chatbot_sessions_require_authentication():
    client = TestClient(app)
    response = client.get("/api/v1/chatbot/sessions")

    assert response.status_code == 401
    assert response.json()["detail"] == "Bearer token is required."


def test_chatbot_message_creation_requires_authentication():
    client = TestClient(app)
    response = client.post(
        "/api/v1/chatbot/sessions/session-1/messages",
        json={"question": "Which schemes can help me?"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Bearer token is required."


def test_authenticated_chat_session_creation(monkeypatch):
    expected = {
        "session": {
            "id": "session-1",
            "user_id": "user-1",
            "title": "New chat",
            "created_at": "2026-06-29T00:00:00Z",
            "updated_at": "2026-06-29T00:00:00Z",
        }
    }

    def create_session(access_token: str, title: str | None = None):
        assert access_token == "test-token"
        assert title == "New chat"
        return expected

    monkeypatch.setattr(chatbot.chat_session_service, "create_session", create_session)

    client = TestClient(app)
    response = client.post(
        "/api/v1/chatbot/sessions",
        headers=AUTH_HEADERS,
        json={"title": "New chat"},
    )

    assert response.status_code == 200
    assert response.json() == expected


def test_chatbot_session_retrieval(monkeypatch):
    expected = {
        "session": {
            "id": "session-1",
            "user_id": "user-1",
            "title": "Scholarships",
            "created_at": "2026-06-29T00:00:00Z",
            "updated_at": "2026-06-29T00:01:00Z",
        },
        "messages": [
            {
                "id": "message-1",
                "session_id": "session-1",
                "user_id": "user-1",
                "role": "user",
                "content": "Scholarships?",
                "sources": [],
                "follow_ups": [],
                "created_at": "2026-06-29T00:00:30Z",
            }
        ],
    }

    def get_session(access_token: str, session_id: str):
        assert access_token == "test-token"
        assert session_id == "session-1"
        return expected

    monkeypatch.setattr(chatbot.chat_session_service, "get_session", get_session)

    client = TestClient(app)
    response = client.get("/api/v1/chatbot/sessions/session-1", headers=AUTH_HEADERS)

    assert response.status_code == 200
    assert response.json() == expected


def test_chatbot_session_ownership_enforcement_returns_404(monkeypatch):
    def get_session(access_token: str, session_id: str):
        assert access_token == "test-token"
        assert session_id == "other-user-session"
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found.",
        )

    monkeypatch.setattr(chatbot.chat_session_service, "get_session", get_session)

    client = TestClient(app)
    response = client.get(
        "/api/v1/chatbot/sessions/other-user-session",
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Chat session not found."


def test_action_links_are_deduped_before_api_response():
    links = chatbot._dedupe_action_links(
        [
            {
                "label": "Open Official Source",
                "url": "HTTPS://Scholarships.Gov.In/?a=1&a=1#section",
                "is_official": True,
            },
            {
                "label": "Apply Here",
                "url": "https://scholarships.gov.in?a=1",
                "is_official": True,
            },
            {
                "label": "Open Official Portal",
                "url": "https://scholarships.gov.in/?a=1&a=2",
                "is_official": True,
            },
        ]
    )

    assert links == [
        {
            "label": "Open Official Source",
            "url": "HTTPS://Scholarships.Gov.In/?a=1&a=1#section",
            "is_official": True,
        },
        {
            "label": "Open Official Portal",
            "url": "https://scholarships.gov.in/?a=1&a=2",
            "is_official": True,
        },
    ]


def test_authenticated_chat_message_creation_persists_user_and_assistant(monkeypatch):
    calls = []

    def add_message(
        access_token: str,
        session_id: str,
        role: str,
        content: str,
        sources=None,
        follow_ups=None,
    ):
        assert access_token == "test-token"
        assert session_id == "session-1"
        calls.append(
            {
                "role": role,
                "content": content,
                "sources": sources or [],
                "follow_ups": follow_ups or [],
            }
        )
        return {
            "message": {
                "id": f"{role}-message",
                "session_id": session_id,
                "user_id": "user-1",
                "role": role,
                "content": content,
                "sources": sources or [],
                "follow_ups": follow_ups or [],
                "created_at": "2026-06-29T00:00:00Z",
            }
        }

    def recent_messages(access_token: str, session_id: str, limit: int = 15):
        assert access_token == "test-token"
        assert session_id == "session-1"
        assert limit == 15
        return [{"role": "user", "content": "Earlier question"}]

    def answer_personalized_question(access_token: str, question: str, history=None):
        assert access_token == "test-token"
        assert question == "Which scholarships are available?"
        assert history == [{"role": "user", "content": "Earlier question"}]
        return {
            "answer": "The scholarship source answer.",
            "sources": [
                {
                    "type": "scheme",
                    "scheme_id": "scheme-1",
                    "title": "Scholarship Scheme",
                    "category": "Scholarship",
                    "state": "All India",
                    "application_link": "https://example.gov.in",
                }
            ],
            "used_profile": True,
            "used_web_search": False,
        }

    def get_session(access_token: str, session_id: str):
        assert access_token == "test-token"
        assert session_id == "session-1"
        return {
            "session": {
                "id": "session-1",
                "user_id": "user-1",
                "title": "Which scholarships are available?",
                "created_at": "2026-06-29T00:00:00Z",
                "updated_at": "2026-06-29T00:01:00Z",
            },
            "messages": [],
        }

    monkeypatch.setattr(chatbot.chat_session_service, "add_message", add_message)
    monkeypatch.setattr(chatbot.chat_session_service, "recent_messages", recent_messages)
    monkeypatch.setattr(
        chatbot.chatbot_service,
        "answer_personalized_question",
        answer_personalized_question,
    )
    monkeypatch.setattr(chatbot.chat_session_service, "get_session", get_session)

    client = TestClient(app)
    response = client.post(
        "/api/v1/chatbot/sessions/session-1/messages",
        headers=AUTH_HEADERS,
        json={"question": "Which scholarships are available?"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["session"]["id"] == "session-1"
    assert body["user_message"]["role"] == "user"
    assert body["assistant_message"]["role"] == "assistant"
    assert body["assistant_message"]["sources"][0]["scheme_id"] == "scheme-1"
    assert body["assistant_message"]["follow_ups"]
    assert body["assistant_message"]["used_profile"] is True
    assert body["assistant_message"]["used_web_search"] is False
    assert [call["role"] for call in calls] == ["user", "assistant"]


def test_chatbot_failure_persists_friendly_assistant_message(monkeypatch):
    calls = []

    def add_message(
        access_token: str,
        session_id: str,
        role: str,
        content: str,
        sources=None,
        follow_ups=None,
    ):
        calls.append({"role": role, "content": content})
        return {
            "message": {
                "id": f"{role}-message",
                "session_id": session_id,
                "user_id": "user-1",
                "role": role,
                "content": content,
                "sources": sources or [],
                "follow_ups": follow_ups or [],
                "created_at": "2026-06-29T00:00:00Z",
            }
        }

    monkeypatch.setattr(chatbot.chat_session_service, "add_message", add_message)
    monkeypatch.setattr(chatbot.chat_session_service, "recent_messages", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        chatbot.chatbot_service,
        "answer_personalized_question",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("Chroma unavailable")),
    )
    monkeypatch.setattr(
        chatbot.chat_session_service,
        "get_session",
        lambda *args, **kwargs: {
            "session": {
                "id": "session-1",
                "user_id": "user-1",
                "title": "New chat",
                "created_at": "2026-06-29T00:00:00Z",
                "updated_at": "2026-06-29T00:00:00Z",
            },
            "messages": [],
        },
    )

    client = TestClient(app)
    response = client.post(
        "/api/v1/chatbot/sessions/session-1/messages",
        headers=AUTH_HEADERS,
        json={"question": "Will this fail?"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["assistant_message"]["content"] == "I could not answer that right now. Please try again in a moment."
    assert body["assistant_message"]["used_profile"] is False
    assert body["assistant_message"]["used_web_search"] is False
    assert [call["role"] for call in calls] == ["user", "assistant"]
