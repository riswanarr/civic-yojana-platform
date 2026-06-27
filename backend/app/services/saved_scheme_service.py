from typing import Any

from fastapi import HTTPException, status
from supabase import create_client

from app.config import settings


class SavedSchemeService:
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

    def list_saved_schemes(self, access_token: str) -> dict[str, Any]:
        user_id = self._get_authenticated_user_id(access_token)
        response = (
            self.client.table("saved_schemes")
            .select("scheme_id,created_at,schemes(*)")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )

        items = []
        for row in response.data or []:
            scheme = row.get("schemes")
            if isinstance(scheme, dict):
                items.append({**scheme, "saved_at": row.get("created_at")})

        return {"items": items}

    def save_scheme(self, access_token: str, scheme_id: str) -> dict[str, Any]:
        user_id = self._get_authenticated_user_id(access_token)
        response = (
            self.client.table("saved_schemes")
            .upsert(
                {"user_id": user_id, "scheme_id": scheme_id},
                on_conflict="user_id,scheme_id",
            )
            .execute()
        )

        return {"saved": True, "scheme_id": scheme_id, "item": (response.data or [None])[0]}

    def unsave_scheme(self, access_token: str, scheme_id: str) -> dict[str, Any]:
        user_id = self._get_authenticated_user_id(access_token)
        (
            self.client.table("saved_schemes")
            .delete()
            .eq("user_id", user_id)
            .eq("scheme_id", scheme_id)
            .execute()
        )

        return {"saved": False, "scheme_id": scheme_id}

    def _get_authenticated_user_id(self, access_token: str) -> str:
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


saved_scheme_service = SavedSchemeService()
