from typing import Any

from fastapi import HTTPException, status
from supabase import create_client

from app.config import settings


class SchemeService:
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

    def list_schemes(
        self,
        *,
        state: str | None = None,
        category: str | None = None,
        ministry: str | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 12,
    ) -> dict[str, Any]:
        start = (page - 1) * page_size
        end = start + page_size - 1

        query = self.client.table("schemes").select("*", count="exact")

        if state:
            query = query.ilike("state", f"%{state}%")
        if category:
            query = query.ilike("category", category)
        if ministry:
            query = query.ilike("ministry", ministry)
        if search:
            escaped_search = search.replace("%", "\\%").replace("_", "\\_")
            search_pattern = f"%{escaped_search}%"
            query = query.or_(
                ",".join(
                    [
                        f"title.ilike.{search_pattern}",
                        f"description.ilike.{search_pattern}",
                        f"ministry.ilike.{search_pattern}",
                        f"category.ilike.{search_pattern}",
                        f"state.ilike.{search_pattern}",
                    ]
                )
            )

        response = query.order("created_at", desc=True).range(start, end).execute()

        return {
            "items": response.data or [],
            "page": page,
            "page_size": page_size,
            "total": response.count or 0,
        }

    def get_scheme(self, scheme_id: str) -> dict[str, Any]:
        response = self.client.table("schemes").select("*").eq("id", scheme_id).limit(1).execute()

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scheme not found.",
            )

        return response.data[0]


scheme_service = SchemeService()
