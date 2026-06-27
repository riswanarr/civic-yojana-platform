from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.services.chatbot_service import (
    GEMINI_QUOTA_UNAVAILABLE_RESPONSE,
    GeminiQuotaExceededError,
    chatbot_service,
)

router = APIRouter()


class ChatbotRequest(BaseModel):
    question: str = Field(min_length=1)


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
