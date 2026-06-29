from __future__ import annotations

import logging
import re
from html.parser import HTMLParser
from io import BytesIO
from typing import Any
from urllib.parse import parse_qs, quote_plus, unquote, urljoin, urlparse

import httpx


OFFICIAL_DOMAINS = (
    ".gov.in",
    ".nic.in",
    "india.gov.in",
    "myscheme.gov.in",
    "scholarships.gov.in",
    "startupindia.gov.in",
    "ncs.gov.in",
    "pminternship.mca.gov.in",
)
OFFICIAL_URL_OVERRIDES = {
    "ssc": "https://ssc.gov.in",
    "staff selection commission": "https://ssc.gov.in",
    "nsp": "https://scholarships.gov.in",
    "national scholarship portal": "https://scholarships.gov.in",
}

SEARCH_URL = "https://duckduckgo.com/html/"
USER_AGENT = "Mozilla/5.0 (compatible; GovernmentSchemesBot/1.0)"
MAX_HTML_BYTES = 1_000_000
MAX_PDF_BYTES = 3_000_000
MAX_EXTRACTED_CHARS = 3_800
MAX_PDF_PAGES = 5
UNVERIFIED_TEXT = "I could not verify this information from official sources."
UNVERIFIED_WEB_RESULT = {
    "type": "web",
    "title": "Official source verification",
    "url": "",
    "snippet": UNVERIFIED_TEXT,
    "content": UNVERIFIED_TEXT,
    "verified": False,
    "official_page_state": "inaccessible",
}
PLACEHOLDER_PHRASES = (
    "new experience loading",
    "portal is now live",
    "stay tuned",
    "loading",
    "coming soon",
    "countdown",
    "migrated portal",
    "upgraded portal",
    "enhanced experience",
    "launching soon",
)
MAINTENANCE_PHRASES = (
    "under maintenance",
    "maintenance",
    "temporarily unavailable",
    "service unavailable",
)
USEFUL_SCHEME_TERMS = (
    "scheme",
    "scholarship",
    "deadline",
    "last date",
    "eligibility",
    "application",
    "renewal",
    "notification",
    "guidelines",
    "documents",
    "subsidy",
    "benefit",
    "registration",
    "status",
)

logger = logging.getLogger(__name__)


class VisibleTextParser(HTMLParser):
    ignored_tags = {"script", "style", "noscript", "svg", "nav", "header", "footer"}

    def __init__(self) -> None:
        super().__init__()
        self._ignored_depth = 0
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() in self.ignored_tags:
            self._ignored_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in self.ignored_tags and self._ignored_depth > 0:
            self._ignored_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._ignored_depth == 0:
            cleaned = data.strip()
            if cleaned:
                self._parts.append(cleaned)

    def text(self) -> str:
        return re.sub(r"\s+", " ", " ".join(self._parts)).strip()


class WebSearchService:
    def search_official_sources(
        self,
        query: str,
        limit: int = 3,
    ) -> list[dict[str, Any]]:
        cleaned_query = query.strip()
        if not cleaned_query:
            return [UNVERIFIED_WEB_RESULT]

        search_query = (
            f"{cleaned_query} "
            "(site:gov.in OR site:nic.in OR site:scholarships.gov.in OR site:startupindia.gov.in)"
        )

        try:
            response = httpx.get(
                SEARCH_URL,
                params={"q": search_query},
                headers={"User-Agent": USER_AGENT},
                timeout=6,
                follow_redirects=True,
            )
            response.raise_for_status()
        except Exception:
            return [UNVERIFIED_WEB_RESULT]

        results = self._parse_results(response.text, limit=limit)
        if not results:
            return [UNVERIFIED_WEB_RESULT]

        enriched_results = self._enrich_results(results[:limit])
        return enriched_results or [UNVERIFIED_WEB_RESULT]

    def _parse_results(self, html: str, limit: int) -> list[dict[str, Any]]:
        matches = re.findall(
            r'<a[^>]+class="[^"]*result__a[^"]*"[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
            html,
            flags=re.IGNORECASE | re.DOTALL,
        )
        snippets = re.findall(
            r'<a[^>]+class="[^"]*result__snippet[^"]*"[^>]*>(.*?)</a>',
            html,
            flags=re.IGNORECASE | re.DOTALL,
        )

        results: list[dict[str, Any]] = []
        for index, (url, title) in enumerate(matches):
            cleaned_url = self._clean_result_url(self._clean_html(url))
            if not self._is_official_url(cleaned_url):
                continue

            snippet = snippets[index] if index < len(snippets) else ""
            results.append(
                {
                    "type": "web",
                    "title": self._clean_html(title),
                    "url": cleaned_url,
                    "snippet": self._clean_html(snippet),
                    "content": "",
                    "verified": True,
                    "official_page_state": "verified",
                }
            )

            if len(results) >= limit:
                break

        return results

    def _enrich_results(self, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        enriched_results = []
        with httpx.Client(
            headers={"User-Agent": USER_AGENT},
            timeout=8,
            follow_redirects=True,
        ) as client:
            for result in results:
                enriched_result = dict(result)
                reachable_url = self._resolve_reachable_official_url(client, result)
                if not reachable_url:
                    logger.info(
                        "official_page_fetch official_url=%s page_state=inaccessible extracted_text_length=0",
                        result.get("url") or "",
                    )
                    continue

                enriched_result["url"] = reachable_url
                extracted_text = self._fetch_official_text(client, reachable_url)
                page_state = self._classify_official_page_state(extracted_text)
                logger.info(
                    "official_page_fetch official_url=%s page_state=%s extracted_text_length=%s",
                    reachable_url,
                    page_state,
                    len(extracted_text),
                )
                enriched_result["official_page_state"] = page_state
                if extracted_text:
                    enriched_result["content"] = extracted_text
                    enriched_result["snippet"] = result.get("snippet") or extracted_text[:300]
                    enriched_result["verified"] = page_state == "verified"
                else:
                    enriched_result["content"] = UNVERIFIED_TEXT
                    enriched_result["verified"] = False
                enriched_results.append(enriched_result)

        return enriched_results

    def _resolve_reachable_official_url(
        self,
        client: httpx.Client,
        result: dict[str, Any],
    ) -> str:
        url = str(result.get("url") or "").strip()
        reachable_url = self._verify_official_url_reachable(client, url)
        if reachable_url:
            return reachable_url

        override_url = self._override_url_for_stale_result(result)
        if override_url and override_url != url:
            return self._verify_official_url_reachable(client, override_url)

        return ""

    def _verify_official_url_reachable(self, client: httpx.Client, url: str) -> str:
        if not url or not self._is_official_url(url):
            return ""

        if hasattr(client, "head"):
            try:
                response = client.head(url)
                status_code = getattr(response, "status_code", 200)
                if status_code < 400:
                    final_url = str(getattr(response, "url", url))
                    if self._is_official_url(final_url):
                        return final_url
                if status_code not in {403, 405}:
                    return ""
            except Exception:
                pass

        try:
            response = client.get(url)
            response.raise_for_status()
        except Exception:
            return ""

        final_url = str(getattr(response, "url", url))
        return final_url if self._is_official_url(final_url) else ""

    def _override_url_for_stale_result(self, result: dict[str, Any]) -> str:
        haystack = " ".join(
            str(result.get(field) or "")
            for field in ("title", "url", "snippet")
        ).lower()

        for key, override_url in OFFICIAL_URL_OVERRIDES.items():
            if key in haystack:
                return override_url

        return ""

    def _fetch_official_text(self, client: httpx.Client, url: str) -> str:
        if not self._is_official_url(url):
            return ""

        downloaded = self._download_limited(client, url)
        if not downloaded:
            return ""

        final_url = downloaded["url"]
        if not self._is_official_url(final_url):
            return ""

        content = downloaded["content"]
        content_type = downloaded["headers"].get("content-type", "").lower()
        if "application/pdf" in content_type or final_url.lower().split("?", 1)[0].endswith(".pdf"):
            return self._extract_pdf_text(content)

        try:
            html = content.decode("utf-8", errors="ignore")
        except Exception:
            return ""

        return self._limit_text(self._extract_visible_text(html))

    def _download_limited(
        self,
        client: httpx.Client,
        url: str,
    ) -> dict[str, Any] | None:
        max_bytes = MAX_PDF_BYTES if url.lower().split("?", 1)[0].endswith(".pdf") else MAX_HTML_BYTES

        if hasattr(client, "stream"):
            try:
                with client.stream("GET", url) as response:
                    response.raise_for_status()
                    final_url = str(response.url)
                    content_type = response.headers.get("content-type", "").lower()
                    if "application/pdf" in content_type:
                        max_bytes = MAX_PDF_BYTES

                    chunks = []
                    total_size = 0
                    for chunk in response.iter_bytes():
                        total_size += len(chunk)
                        if total_size > max_bytes:
                            return None
                        chunks.append(chunk)

                    return {
                        "url": final_url,
                        "headers": dict(response.headers),
                        "content": b"".join(chunks),
                    }
            except Exception:
                return None

        try:
            response = client.get(url)
            response.raise_for_status()
        except Exception:
            return None

        content_type = response.headers.get("content-type", "").lower()
        if "application/pdf" in content_type:
            max_bytes = MAX_PDF_BYTES
        if len(response.content) > max_bytes:
            return None

        return {
            "url": str(response.url),
            "headers": dict(response.headers),
            "content": response.content,
        }

    def _extract_visible_text(self, html: str) -> str:
        parser = VisibleTextParser()
        try:
            parser.feed(html)
        except Exception:
            return ""

        return self._limit_text(parser.text())

    def _extract_pdf_text(self, content: bytes) -> str:
        try:
            from pypdf import PdfReader
        except Exception:
            return ""

        try:
            reader = PdfReader(BytesIO(content))
            text_parts = []
            for page in reader.pages[:MAX_PDF_PAGES]:
                page_text = page.extract_text() or ""
                if page_text.strip():
                    text_parts.append(page_text)
            return self._limit_text(" ".join(text_parts))
        except Exception:
            return ""

    def _limit_text(self, text: str) -> str:
        cleaned = re.sub(r"\s+", " ", text).strip()
        return cleaned[:MAX_EXTRACTED_CHARS]

    def _classify_official_page_state(self, text: str) -> str:
        cleaned = re.sub(r"\s+", " ", text or "").strip().lower()
        if not cleaned:
            return "inaccessible"

        maintenance_hits = sum(1 for phrase in MAINTENANCE_PHRASES if phrase in cleaned)
        placeholder_hits = sum(1 for phrase in PLACEHOLDER_PHRASES if phrase in cleaned)
        useful_hits = sum(1 for term in USEFUL_SCHEME_TERMS if term in cleaned)
        has_date_like_text = bool(
            re.search(r"\b\d{1,2}\s+[a-z]{3,9}\s+\d{4}\b|\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b", cleaned)
        )

        if maintenance_hits and useful_hits < 2 and not has_date_like_text:
            return "maintenance"
        if placeholder_hits and useful_hits < 2 and not has_date_like_text:
            return "placeholder"

        return "verified"

    def _clean_result_url(self, url: str) -> str:
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        redirect_values = query.get("uddg") or query.get("u")
        if redirect_values:
            return unquote(redirect_values[0])

        if parsed.scheme:
            return url

        return urljoin(SEARCH_URL, url)

    def _is_official_url(self, url: str) -> bool:
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        return any(host == domain or host.endswith(domain) for domain in OFFICIAL_DOMAINS)

    def _clean_html(self, value: str) -> str:
        cleaned = re.sub(r"<[^>]+>", " ", value)
        cleaned = cleaned.replace("&amp;", "&").replace("&quot;", '"').replace("&#x27;", "'")
        cleaned = cleaned.replace("&lt;", "<").replace("&gt;", ">")
        return re.sub(r"\s+", " ", cleaned).strip()

    def build_search_url(self, query: str) -> str:
        return f"{SEARCH_URL}?q={quote_plus(query)}"


web_search_service = WebSearchService()
