from typing import Any
import logging

from fastapi import HTTPException, status
from supabase import create_client

from app.config import settings


NOTIFICATION_FIELDS = "id,user_id,title,message,is_read,created_at,scheme_id"
logger = logging.getLogger(__name__)


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

        return {
            "items": notifications,
            "unread_count": sum(1 for item in notifications if not item.get("is_read")),
        }

    def create_from_recommendations(
        self,
        user_id: str,
        recommendations: list[dict[str, Any]],
    ) -> int:
        eligible_recommendations = []
        seen_keys = set()
        for recommendation in recommendations:
            if not self._should_notify(recommendation):
                continue

            equivalent_key = recommendation.get("equivalent_key") or recommendation.get("scheme_id")
            if equivalent_key in seen_keys:
                continue

            seen_keys.add(equivalent_key)
            eligible_recommendations.append(recommendation)

        if not eligible_recommendations:
            return 0

        rows = [
            {
                "user_id": user_id,
                "scheme_id": recommendation["scheme_id"],
                "title": "Strong scheme match available",
                "message": f"{recommendation['title']} matches your profile with a {recommendation['score']}% score.",
                "is_read": False,
            }
            for recommendation in eligible_recommendations
        ]

        return self.insert_idempotent_notifications(rows)

    def insert_idempotent_notifications(
        self,
        rows: list[dict[str, Any]],
        *,
        client: Any | None = None,
    ) -> int:
        if not rows:
            return 0

        db = client or self.client
        rows_to_insert = []
        seen_keys = set()

        for row in rows:
            user_id = row.get("user_id")
            scheme_id = row.get("scheme_id")
            title = row.get("title")

            if not user_id or not scheme_id or not title:
                continue

            key = (user_id, scheme_id, title)
            if key in seen_keys:
                continue

            seen_keys.add(key)

            try:
                existing_response = (
                    db.table("notifications")
                    .select("id")
                    .eq("user_id", user_id)
                    .eq("scheme_id", scheme_id)
                    .eq("title", title)
                    .limit(1)
                    .execute()
                )
            except Exception:
                logger.exception("Unable to check existing notification.")
                continue

            if existing_response.data:
                continue

            rows_to_insert.append(row)

        if not rows_to_insert:
            return 0

        try:
            response = db.table("notifications").insert(rows_to_insert).execute()
            return len(response.data or rows_to_insert)
        except Exception:
            logger.exception("Unable to create notifications.")
            return 0

    def _should_notify(self, recommendation: dict[str, Any]) -> bool:
        try:
            score = int(recommendation.get("score", 0))
        except (TypeError, ValueError):
            score = 0

        reason = str(recommendation.get("reason") or "").lower()

        return (
            bool(recommendation.get("scheme_id"))
            and bool(recommendation.get("scheme_type"))
            and score >= 70
            and recommendation.get("hard_restrictions_passed", True)
            and not recommendation.get("additional_verification_required", False)
            and "uncertain" not in reason
            and "low match" not in reason
        )

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
