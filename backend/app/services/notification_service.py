from typing import Any

from fastapi import HTTPException, status
from supabase import create_client

from app.config import settings


NOTIFICATION_FIELDS = "id,user_id,title,message,is_read,created_at,scheme_id"


class NotificationService:
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

    def list_notifications(self, access_token: str) -> dict[str, Any]:
        user_id = self._get_authenticated_user_id(access_token)
        notifications = self._fetch_notifications(user_id)

        if not notifications:
            self._seed_demo_notifications(user_id)
            notifications = self._fetch_notifications(user_id)

        return {
            "items": notifications,
            "unread_count": sum(1 for item in notifications if not item.get("is_read")),
        }

    def mark_as_read(self, access_token: str, notification_id: str) -> dict[str, Any]:
        user_id = self._get_authenticated_user_id(access_token)
        response = (
                    self.client.table("notifications")
                    .update({"is_read": True}).eq("id", notification_id).eq("user_id", user_id).execute())

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found.",
                )

        return {"success": True}
    def _fetch_notifications(self, user_id: str) -> list[dict[str, Any]]:
        response = (
            self.client.table("notifications")
            .select(NOTIFICATION_FIELDS)
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(10)
            .execute()
        )

        return response.data or []

    def _seed_demo_notifications(self, user_id: str) -> None:
        profile = self._fetch_profile(user_id)
        schemes = self._fetch_schemes(profile)

        if not schemes:
            return

        rows = []
        for scheme in schemes[:3]:
            rows.append(
                {
                    "user_id": user_id,
                    "scheme_id": scheme.get("id"),
                    "title": "Scheme match available",
                    "message": f"{scheme.get('title', 'A scheme')} may be relevant for your profile.",
                    "is_read": False,
                }
            )

        if rows:
            self.client.table("notifications").insert(rows).execute()

    def _fetch_profile(self, user_id: str) -> dict[str, Any]:
        response = (
            self.client.table("profiles")
            .select("state,occupation,category,education_level")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )

        return (response.data or [{}])[0]

    def _fetch_schemes(self, profile: dict[str, Any]) -> list[dict[str, Any]]:
        state = str(profile.get("state") or "").strip()
        category = str(profile.get("category") or "").strip()

        query = self.client.table("schemes").select("id,title,category,state").limit(3)

        if state:
            query = query.or_(f"state.ilike.%{state}%,state.ilike.%All India%")
        elif category:
            query = query.ilike("category", f"%{category}%")

        response = query.execute()
        return response.data or []

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


notification_service = NotificationService()
