from typing import Any

from fastapi import HTTPException, status
from supabase import create_client

from app.config import settings


NON_ACTIONABLE_EXACT_TITLES = {
    "schemes",
    "students",
    "jobseeker",
    "application status",
    "apply for scholarship",
    "schemes on nsp",
    "scholarship eligibility",
    "find international jobs",
    "find domestic jobs",
    "find career center",
    "login",
    "register",
    "dashboard",
    "aicte student opportunity update",
}

NON_ACTIONABLE_TITLE_TERMS = [
    "application status",
    "scholarship eligibility",
    "schemes on nsp",
    "apply for scholarship",
    "login",
    "register",
    "dashboard",
    "portal",
    "search schemes",
]

NON_ACTIONABLE_TITLE_PREFIXES = [
    "apply",
    "application",
    "scheme status",
]

NON_ACTIONABLE_DESCRIPTION_TERMS = [
    "navigation page",
    "portal page",
    "status page",
    "information page",
    "search page",
    "verified from",
    "portal",
    "search",
    "application status",
    "login",
    "register",
    "dashboard",
]


def _is_actionable_scheme(scheme: dict[str, Any]) -> bool:
    raw_title = str(scheme.get("title") or "").strip()
    title = raw_title.lower()
    category = str(scheme.get("category") or "").strip().lower()
    description = str(scheme.get("description") or "").strip().lower()

    if not title:
        return False

    if title in NON_ACTIONABLE_EXACT_TITLES:
        return False

    if category and title == category:
        return False

    if any(term in title for term in NON_ACTIONABLE_TITLE_TERMS):
        return False

    if any(title.startswith(prefix) for prefix in NON_ACTIONABLE_TITLE_PREFIXES):
        return False

    if any(term in description for term in NON_ACTIONABLE_DESCRIPTION_TERMS):
        return False

    meaningful_words = [word for word in raw_title.replace("-", " ").split() if word.strip()]
    is_acronym = raw_title.isupper() and raw_title.isalnum() and len(raw_title) >= 3
    if len(meaningful_words) < 2 and not is_acronym:
        return False

    return True


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
        batch_size = max(page_size * 3, 30)
        offset = 0
        actionable_items = []

        while True:
            response = (
                self._build_list_query(
                    state=state,
                    category=category,
                    ministry=ministry,
                    search=search,
                )
                .order("created_at", desc=True)
                .range(offset, offset + batch_size - 1)
                .execute()
            )
            raw_items = response.data or []

            actionable_items.extend(
                item for item in raw_items if _is_actionable_scheme(item)
            )

            if len(raw_items) < batch_size:
                break

            offset += batch_size

        start = (page - 1) * page_size
        end = start + page_size

        return {
            "items": actionable_items[start:end],
            "page": page,
            "page_size": page_size,
            "total": len(actionable_items),
        }

    def get_scheme(self, scheme_id: str) -> dict[str, Any]:
        response = self.client.table("schemes").select("*").eq("id", scheme_id).limit(1).execute()

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scheme not found.",
            )

        return response.data[0]

    def _build_list_query(
        self,
        *,
        state: str | None,
        category: str | None,
        ministry: str | None,
        search: str | None,
    ):
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

        return query


scheme_service = SchemeService()
