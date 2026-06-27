from typing import Any

from app.services.parsers.base_parser import BaseParser


class NCSParser(BaseParser):
    parser_name = "ncs"
    keywords = ("job", "career", "vacancy", "placement", "fair", "employment")

    def fetch(self, source: dict[str, Any]) -> list[dict[str, Any]]:
        try:
            source_url = source.get("url") or "https://www.ncs.gov.in/"
            html = self.fetch_url(source_url)
            items = self._extract_items(source, html, source_url)
            if items:
                return items
        except Exception:
            pass

        return [
            self.mock_opportunity(
                source=source,
                title="National Career Service Job Update",
                description="Job opportunity update from National Career Service.",
                category="Government Job",
            )
        ]

    def _extract_items(self, source: dict[str, Any], html: str, source_url: str) -> list[dict[str, Any]]:
        opportunities: list[dict[str, Any]] = []
        seen_titles: set[str] = set()

        for link in self.extract_links(html, source_url):
            text = link["text"]
            if not self._is_relevant(text):
                continue

            opportunity = self._opportunity(source, text, link["href"])
            opportunities.append(opportunity)
            seen_titles.add(opportunity["title"].lower())

            if len(opportunities) >= 5:
                return opportunities

        for chunk in self.extract_text_chunks(html):
            if not self._is_relevant(chunk) or len(chunk) < 16:
                continue

            title = chunk[:120].strip()
            if title.lower() in seen_titles:
                continue

            opportunities.append(self._opportunity(source, title, source_url))
            seen_titles.add(title.lower())

            if len(opportunities) >= 5:
                break

        return opportunities

    def _is_relevant(self, text: str) -> bool:
        normalized_text = text.lower()
        return any(keyword in normalized_text for keyword in self.keywords)

    def _opportunity(self, source: dict[str, Any], title: str, link: str) -> dict[str, Any]:
        return {
            "title": title,
            "description": f"{title}. Verified from the National Career Service portal.",
            "category": "Government Job",
            "state": "All India",
            "ministry": "Ministry of Labour and Employment",
            "eligibility_criteria": "Refer to the official NCS listing for role-specific eligibility.",
            "benefits": "Employment, job fair, or career service opportunity published through NCS.",
            "application_link": link,
            "official_source": source.get("url") or link,
            "deadline": None,
            "tags": ["jobs", "ncs", "career"],
        }
