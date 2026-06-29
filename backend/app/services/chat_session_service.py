from typing import Any

from fastapi import HTTPException, status
from supabase import create_client

from app.config import settings


SESSION_FIELDS = "id,user_id,title,created_at,updated_at"
MESSAGE_FIELDS = "id,session_id,user_id,role,content,sources,follow_ups,created_at"
DEFAULT_SESSION_TITLE = "New chat"
MAX_SESSION_TITLE_LENGTH = 80


class ChatSessionService:
    def __init__(self) -> None:
        self._client = None

    @property
    def client(self):
        if self._client is None:
            supabase_key = settings.supabase_service_role_key or settings.supabase_anon_key

            if not settings.supabase_url or not supabase_key:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Supabase configuration is missing.",
                )

            self._client = create_client(settings.supabase_url, supabase_key)

        return self._client

    def get_authenticated_user_id(self, access_token: str) -> str:
        try:
            response = self.client.auth.get_user(access_token)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token.",
            ) from exc

        user = getattr(response, "user", None)
        user_id = getattr(user, "id", None)

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authenticated user could not be identified.",
            )

        return str(user_id)

    def list_sessions(self, access_token: str) -> dict[str, list[dict[str, Any]]]:
        user_id = self.get_authenticated_user_id(access_token)
        response = (
            self.client.table("chat_sessions")
            .select(SESSION_FIELDS)
            .eq("user_id", user_id)
            .order("updated_at", desc=True)
            .execute()
        )

        return {"sessions": response.data or []}

    def create_session(
        self,
        access_token: str,
        title: str | None = None,
    ) -> dict[str, Any]:
        user_id = self.get_authenticated_user_id(access_token)
        response = (
            self.client.table("chat_sessions")
            .insert(
                {
                    "user_id": user_id,
                    "title": self._normalize_title(title),
                }
            )
            .execute()
        )

        return {"session": self._first_row(response.data)}

    def get_session(self, access_token: str, session_id: str) -> dict[str, Any]:
        user_id = self.get_authenticated_user_id(access_token)
        session = self._fetch_session(user_id, session_id)
        messages_response = (
            self.client.table("chat_messages")
            .select(MESSAGE_FIELDS)
            .eq("user_id", user_id)
            .eq("session_id", session_id)
            .order("created_at", desc=False)
            .execute()
        )

        return {
            "session": session,
            "messages": messages_response.data or [],
        }

    def delete_session(self, access_token: str, session_id: str) -> dict[str, Any]:
        user_id = self.get_authenticated_user_id(access_token)
        self._fetch_session(user_id, session_id)
        (
            self.client.table("chat_sessions")
            .delete()
            .eq("user_id", user_id)
            .eq("id", session_id)
            .execute()
        )

        return {"deleted": True, "session_id": session_id}

    def add_message(
        self,
        access_token: str,
        session_id: str,
        role: str,
        content: str,
        sources: list[dict[str, Any]] | None = None,
        follow_ups: list[str] | None = None,
    ) -> dict[str, Any]:
        user_id = self.get_authenticated_user_id(access_token)
        self._fetch_session(user_id, session_id)

        cleaned_content = content.strip()
        if not cleaned_content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Message content is required.",
            )

        if role not in {"user", "assistant"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Message role must be user or assistant.",
            )

        response = (
            self.client.table("chat_messages")
            .insert(
                {
                    "session_id": session_id,
                    "user_id": user_id,
                    "role": role,
                    "content": cleaned_content,
                    "sources": sources or [],
                    "follow_ups": follow_ups or [],
                }
            )
            .execute()
        )

        if role == "user":
            self._set_title_from_first_user_message(user_id, session_id, cleaned_content)

        return {"message": self._first_row(response.data)}

    def recent_messages(
        self,
        access_token: str,
        session_id: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        user_id = self.get_authenticated_user_id(access_token)
        self._fetch_session(user_id, session_id)
        response = (
            self.client.table("chat_messages")
            .select(MESSAGE_FIELDS)
            .eq("user_id", user_id)
            .eq("session_id", session_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

        return list(reversed(response.data or []))

    def _fetch_session(self, user_id: str, session_id: str) -> dict[str, Any]:
        response = (
            self.client.table("chat_sessions")
            .select(SESSION_FIELDS)
            .eq("user_id", user_id)
            .eq("id", session_id)
            .limit(1)
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found.",
            )

        return response.data[0]

    def _set_title_from_first_user_message(
        self,
        user_id: str,
        session_id: str,
        content: str,
    ) -> None:
        session = self._fetch_session(user_id, session_id)
        if session.get("title") != DEFAULT_SESSION_TITLE:
            return

        (
            self.client.table("chat_sessions")
            .update({"title": self._normalize_title(content)})
            .eq("user_id", user_id)
            .eq("id", session_id)
            .execute()
        )

    def _normalize_title(self, title: str | None) -> str:
        cleaned_title = (title or DEFAULT_SESSION_TITLE).strip()
        if not cleaned_title:
            return DEFAULT_SESSION_TITLE

        if len(cleaned_title) <= MAX_SESSION_TITLE_LENGTH:
            return cleaned_title

        return f"{cleaned_title[: MAX_SESSION_TITLE_LENGTH - 3]}..."

    def _first_row(self, rows: list[dict[str, Any]] | None) -> dict[str, Any]:
        if not rows:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database operation did not return a row.",
            )

        return rows[0]


chat_session_service = ChatSessionService()
