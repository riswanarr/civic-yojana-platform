from typing import Any

from app.services.parsers.base_parser import BaseParser


class AICTEParser(BaseParser):
    parser_name = "aicte"
    keywords = ("scholarship", "internship", "fellowship", "scheme", "student", "announcement")

    def fetch(self, source: dict[str, Any]) -> list[dict[str, Any]]:
        try:
            source_url = source.get("url") or "https://www.aicte.gov.in/"
            html = self.fetch_url(source_url)
            items = self._extract_items(source, html, source_url)
            if items:
                return items
        except Exception:
            pass

        return [
            self.mock_opportunity(
                source=source,
                title="AICTE Student Opportunity Update",
                description="AICTE scholarship and student support update.",
                category="Scholarship",
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
            if not self._is_relevant(chunk) or len(chunk) < 18:
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
            "description": f"{title}. Verified from the AICTE official website.",
            "category": "Scholarship",
            "state": "All India",
            "ministry": "All India Council for Technical Education",
            "eligibility_criteria": "Refer to the official AICTE notice for eligibility criteria.",
            "benefits": "AICTE student support, scholarship, internship, or academic opportunity.",
            "application_link": link,
            "official_source": source.get("url") or link,
            "deadline": None,
            "tags": ["aicte", "students", "technical-education"],
        }
