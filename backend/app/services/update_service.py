import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from supabase import create_client

from app.config import settings
from app.services.parsers import (
    AICTEParser,
    NCSParser,
    NSPParser,
    PMInternshipParser,
    StartupIndiaParser,
)


logger = logging.getLogger(__name__)


PARSER_REGISTRY = {
    "nsp": NSPParser(),
    "aicte": AICTEParser(),
    "ncs": NCSParser(),
    "pm_internship": PMInternshipParser(),
    "startup_india": StartupIndiaParser(),
}


class UpdateService:
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

    def run_sync(self) -> dict[str, int]:
        sources = self.load_active_sources()
        new_opportunities = 0
        updated_opportunities = 0
        notifications_created = 0

        logger.info("Starting source sync for %s active source(s).", len(sources))

        for source in sources:
            raw_items = self.fetch_source(source)
            normalized_items = self.normalize_data(raw_items)
            sync_result = self.sync_database(normalized_items)
            new_opportunities += sync_result["new_opportunities"]
            updated_opportunities += sync_result["updated_opportunities"]
            notifications_created += self.create_notifications(sync_result["new_items"])
            self._mark_source_checked(source)

        return {
            "sources_checked": len(sources),
            "new_opportunities": new_opportunities,
            "updated_opportunities": updated_opportunities,
            "notifications_created": notifications_created,
        }

    def load_active_sources(self) -> list[dict[str, Any]]:
        response = (
            self.client.table("sources")
            .select("id,name,url,category,source_type,parser_name,last_checked,active")
            .eq("active", True)
            .execute()
        )

        return response.data or []

    def fetch_source(self, source: dict[str, Any]) -> list[dict[str, Any]]:
        parser_name = source.get("parser_name")
        parser = PARSER_REGISTRY.get(str(parser_name))

        if not parser:
            logger.warning("No parser registered for source %s.", parser_name)
            return []

        logger.info("Fetching source %s with parser %s.", source.get("name"), parser_name)
        return parser.fetch(source)

    def normalize_data(self, raw_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        normalized_items = []

        for item in raw_items:
            title = str(item.get("title", "")).strip()
            description = str(item.get("description", "")).strip()
            category = str(item.get("category", "")).strip()

            if not title or not description or not category:
                logger.warning("Skipping invalid opportunity payload: %s", item)
                continue

            normalized_items.append(
                {
                    "title": title,
                    "description": description,
                    "ministry": item.get("ministry"),
                    "state": item.get("state") or "All India",
                    "category": category,
                    "eligibility_criteria": item.get("eligibility_criteria"),
                    "benefits": item.get("benefits"),
                    "application_link": item.get("application_link"),
                    "official_source": item.get("official_source") or item.get("application_link"),
                    "deadline": item.get("deadline"),
                    "tags": item.get("tags") or [],
                }
            )

        return normalized_items

    def sync_database(self, opportunities: list[dict[str, Any]]) -> dict[str, Any]:
        new_items = []
        updated_items = []

        for opportunity in opportunities:
            existing_response = (
                self.client.table("schemes")
                .select("id")
                .eq("title", opportunity["title"])
                .limit(1)
                .execute()
            )
            existing = (existing_response.data or [None])[0]

            if existing:
                self.client.table("schemes").update(opportunity).eq("id", existing["id"]).execute()
                updated_items.append({**opportunity, "id": existing["id"]})
            else:
                insert_response = self.client.table("schemes").insert(opportunity).execute()
                created_item = (insert_response.data or [opportunity])[0]
                new_items.append(created_item)

        return {
            "new_opportunities": len(new_items),
            "updated_opportunities": len(updated_items),
            "new_items": new_items,
            "updated_items": updated_items,
        }

    def create_notifications(self, new_opportunities: list[dict[str, Any]]) -> int:
        if not new_opportunities:
            return 0

        profiles_response = self.client.table("profiles").select("user_id").limit(50).execute()
        user_ids = [profile.get("user_id") for profile in profiles_response.data or [] if profile.get("user_id")]

        notification_rows = []
        for opportunity in new_opportunities:
            for user_id in user_ids:
                notification_rows.append(
                    {
                        "user_id": user_id,
                        "scheme_id": opportunity.get("id"),
                        "title": "New opportunity available",
                        "message": f"{opportunity['title']} was added from a live source.",
                        "is_read": False,
                    }
                )

        if not notification_rows:
            return 0

        response = self.client.table("notifications").insert(notification_rows).execute()
        return len(response.data or notification_rows)

    def _mark_source_checked(self, source: dict[str, Any]) -> None:
        source_id = source.get("id")
        if not source_id:
            return

        self.client.table("sources").update({"last_checked": datetime.now(timezone.utc).isoformat()}).eq("id", source_id).execute()


update_service = UpdateService()
