from typing import Annotated, Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from fastapi import APIRouter, Header, HTTPException, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.services.chat_session_service import chat_session_service
from app.services.chatbot_service import (
    GEMINI_QUOTA_UNAVAILABLE_RESPONSE,
    GeminiQuotaExceededError,
    chatbot_service,
)

router = APIRouter()


class ChatbotRequest(BaseModel):
    question: str = Field(min_length=1)


class CreateChatSessionRequest(BaseModel):
    title: str | None = Field(default=None, max_length=80)


FOLLOW_UP_QUESTIONS = [
    "Scholarships for SC students in Kerala",
    "Jobs after graduation",
    "Schemes for women entrepreneurs",
    "Opportunities for minority students",
]
CHATBOT_FAILURE_RESPONSE = {
    "answer": "I could not answer that right now. Please try again in a moment.",
    "sources": [],
}


def get_access_token(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token is required.",
        )

    access_token = authorization.split(" ", 1)[1].strip()
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token is required.",
        )

    return access_token


def _normalize_action_url(url: Any) -> str:
    raw_url = str(url or "").strip()
    if not raw_url:
        return ""

    try:
        parsed = urlsplit(raw_url)
    except ValueError:
        return raw_url.rstrip("/").lower()

    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip("/")
    seen_params = set()
    query_params = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        param_key = (key, value)
        if param_key in seen_params:
            continue
        seen_params.add(param_key)
        query_params.append((key, value))

    return urlunsplit((scheme, netloc, path, urlencode(query_params), ""))


def _dedupe_action_links(action_links: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen_urls = set()
    deduped_links = []
    for link in action_links:
        normalized_url = _normalize_action_url(link.get("url"))
        if not normalized_url or normalized_url in seen_urls:
            continue
        seen_urls.add(normalized_url)
        deduped_links.append(link)

    return deduped_links


@router.post("")
def ask_chatbot(payload: ChatbotRequest) -> Any:
    try:
        return chatbot_service.answer_question(payload.question)
    except GeminiQuotaExceededError:
        return JSONResponse(
            status_code=503,
            content=GEMINI_QUOTA_UNAVAILABLE_RESPONSE,
        )


@router.get("/retrieve")
def retrieve_sources(
    q: str = Query(min_length=1),
    limit: int = Query(default=5, ge=1, le=10),
) -> dict[str, Any]:
    return {
        "sources": chatbot_service.retrieve_sources(q, limit=limit),
    }


@router.get("/sessions")
def list_chat_sessions(
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, list[dict[str, Any]]]:
    return chat_session_service.list_sessions(get_access_token(authorization))


@router.post("/sessions")
def create_chat_session(
    payload: CreateChatSessionRequest | None = None,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    return chat_session_service.create_session(
        get_access_token(authorization),
        title=payload.title if payload else None,
    )


@router.get("/sessions/{session_id}")
def get_chat_session(
    session_id: str,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    return chat_session_service.get_session(get_access_token(authorization), session_id)


@router.delete("/sessions/{session_id}")
def delete_chat_session(
    session_id: str,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    return chat_session_service.delete_session(get_access_token(authorization), session_id)


@router.post("/sessions/{session_id}/messages")
def create_chat_message(
    session_id: str,
    payload: ChatbotRequest,
    authorization: Annotated[str | None, Header()] = None,
) -> Any:
    access_token = get_access_token(authorization)
    user_message = chat_session_service.add_message(
        access_token,
        session_id,
        role="user",
        content=payload.question,
    )["message"]
    recent_history = chat_session_service.recent_messages(access_token, session_id, limit=15)

    try:
        chatbot_response = chatbot_service.answer_personalized_question(
            access_token,
            payload.question,
            history=recent_history,
        )
    except GeminiQuotaExceededError:
        return _persist_assistant_response(
            access_token,
            session_id,
            user_message,
            GEMINI_QUOTA_UNAVAILABLE_RESPONSE,
            follow_ups=[],
        )
    except HTTPException as exc:
        if exc.status_code < 500:
            raise

        return _persist_assistant_response(
            access_token,
            session_id,
            user_message,
            CHATBOT_FAILURE_RESPONSE,
            follow_ups=[],
        )
    except Exception:
        return _persist_assistant_response(
            access_token,
            session_id,
            user_message,
            CHATBOT_FAILURE_RESPONSE,
            follow_ups=[],
        )

    assistant_message = chat_session_service.add_message(
        access_token,
        session_id,
        role="assistant",
        content=chatbot_response.get("answer")
        or "I could not find a clear answer for that question.",
        sources=chatbot_response.get("sources") or [],
        follow_ups=chatbot_response.get("follow_ups") or FOLLOW_UP_QUESTIONS,
    )["message"]
    assistant_message["used_profile"] = bool(chatbot_response.get("used_profile"))
    assistant_message["used_web_search"] = bool(chatbot_response.get("used_web_search"))
    assistant_message["action_links"] = _dedupe_action_links(chatbot_response.get("action_links") or [])
    session = chat_session_service.get_session(access_token, session_id)["session"]

    return {
        "session": session,
        "user_message": user_message,
        "assistant_message": assistant_message,
    }


def _persist_assistant_response(
    access_token: str,
    session_id: str,
    user_message: dict[str, Any],
    response_payload: dict[str, Any],
    follow_ups: list[str],
) -> dict[str, Any]:
    assistant_message = chat_session_service.add_message(
        access_token,
        session_id,
        role="assistant",
        content=response_payload.get("answer")
        or "I could not answer that right now. Please try again in a moment.",
        sources=response_payload.get("sources") or [],
        follow_ups=follow_ups,
    )["message"]
    assistant_message["used_profile"] = False
    assistant_message["used_web_search"] = False
    session = chat_session_service.get_session(access_token, session_id)["session"]

    return {
        "session": session,
        "user_message": user_message,
        "assistant_message": assistant_message,
    }
