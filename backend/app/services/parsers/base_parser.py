from abc import ABC, abstractmethod
from html import unescape
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin
from urllib.request import Request, urlopen


class LinkTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[dict[str, str]] = []
        self._current_href: str | None = None
        self._current_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return

        attributes = dict(attrs)
        self._current_href = attributes.get("href")
        self._current_text = []

    def handle_data(self, data: str) -> None:
        if self._current_href:
            self._current_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "a" or not self._current_href:
            return

        text = " ".join(" ".join(self._current_text).split())
        if text:
            self.links.append({"href": self._current_href, "text": unescape(text)})

        self._current_href = None
        self._current_text = []


class TextContentParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"script", "style", "noscript"}:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "noscript"} and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return

        text = " ".join(data.split())
        if text:
            self.parts.append(unescape(text))


class BaseParser(ABC):
    parser_name: str
    user_agent = "civic-yojana-sync/1.0"

    @abstractmethod
    def fetch(self, source: dict[str, Any]) -> list[dict[str, Any]]:
        raise NotImplementedError

    def fetch_url(self, url: str) -> str:
        request = Request(url, headers={"User-Agent": self.user_agent})
        with urlopen(request, timeout=15) as response:
            return response.read().decode("utf-8", errors="ignore")

    def extract_links(self, html: str, base_url: str) -> list[dict[str, str]]:
        parser = LinkTextParser()
        parser.feed(html)

        return [
            {
                "text": link["text"],
                "href": urljoin(base_url, link["href"]),
            }
            for link in parser.links
        ]

    def extract_text_chunks(self, html: str) -> list[str]:
        parser = TextContentParser()
        parser.feed(html)
        return parser.parts

    def mock_opportunity(
        self,
        *,
        source: dict[str, Any],
        title: str,
        description: str,
        category: str,
    ) -> dict[str, Any]:
        return {
            "title": title,
            "description": description,
            "category": category,
            "state": "All India",
            "ministry": None,
            "eligibility_criteria": "Eligibility details will be verified from the official source.",
            "benefits": "Benefits will be verified from the official source.",
            "application_link": source.get("url"),
            "official_source": source.get("url"),
            "deadline": None,
            "tags": [category.lower(), self.parser_name],
        }
