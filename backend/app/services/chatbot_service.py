from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any

import chromadb
from fastapi import HTTPException, status
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from supabase import create_client

from app.config import settings
from app.services.web_search_service import web_search_service


BACKEND_DIR = Path(__file__).resolve().parents[2]
VECTOR_DB_DIR = BACKEND_DIR / "app" / "data" / "chroma_schemes"
COLLECTION_NAME = "schemes"
EMBEDDING_MODEL = "models/gemini-embedding-001"
RECENT_UPDATE_KEYWORDS = (
    "deadline",
    "last date",
    "renewal",
    "renew",
    "application status",
    "status check",
    "latest notification",
    "notification",
    "circular",
    "announcement",
    "applications are open",
    "application open",
    "recent updates",
    "currently",
    "today",
)
INTERNAL_WEB_FALLBACK_TITLE = "Official source verification"
MAX_RESPONSE_SOURCES = 3
INSUFFICIENT_RELEVANCE_RESPONSE = (
    "Answer\n"
    "\u2022 I could not find sufficiently relevant schemes for this query from the available knowledge base.\n\n"
    "Next Steps\n"
    "\u2022 Try a more specific search.\n"
    "\u2022 Search by state, category, or beneficiary type."
)
DYNAMIC_UNVERIFIED_RESPONSE = (
    "Answer\n"
    "• I could not verify this information from official sources.\n\n"
    "Next Steps\n"
    "• Check the latest notifications on the official portal.\n"
    "• Review recent announcements."
)
DYNAMIC_PORTAL_PLACEHOLDER_RESPONSE = (
    "Answer\n"
    "â€¢ The official portal is currently displaying a transition or loading page and does not expose the requested information in a machine-readable format.\n\n"
    "Next Steps\n"
    "â€¢ Open the official portal.\n"
    "â€¢ Check Latest Notifications.\n"
    "â€¢ Review scheme guidelines or PDF notices.\n"
    "â€¢ Try again later if the portal has recently migrated."
)
DYNAMIC_UNVERIFIED_RESPONSE = (
    "Answer\n"
    "\u2022 I could not verify the current information because official sources did not expose the requested details in a machine-readable format.\n\n"
    "Next Steps\n"
    "\u2022 Open the official portal.\n"
    "\u2022 Check the latest notifications.\n"
    "\u2022 Review any available guidelines or PDFs."
)
DYNAMIC_PORTAL_PLACEHOLDER_RESPONSE = (
    "Answer\n"
    "\u2022 The official portal is currently displaying a transition or loading page and does not expose the requested information in a machine-readable format.\n\n"
    "Next Steps\n"
    "\u2022 Open the official portal.\n"
    "\u2022 Check Latest Notifications.\n"
    "\u2022 Review scheme guidelines or PDF notices.\n"
    "\u2022 Try again later if the portal has recently migrated."
)
PROFILE_FIELDS = (
    "age,gender,state,occupation,education_level,annual_family_income,"
    "category,disability_status,minority_status"
)
GEMINI_QUOTA_UNAVAILABLE_RESPONSE = {
    "answer": "AI responses are temporarily unavailable because the Gemini API quota has been reached. Please try again later.",
    "sources": [],
}


class GeminiQuotaExceededError(Exception):
    pass


def _is_gemini_quota_or_api_error(exc: Exception) -> bool:
    module_name = exc.__class__.__module__
    class_name = exc.__class__.__name__.lower()
    message = str(exc).lower()

    return (
        "google.api_core.exceptions" in module_name
        or "resourceexhausted" in class_name
        or "quota" in message
        or "429" in message
        or "rate limit" in message
        or "resource exhausted" in message
    )


class ChatbotService:
    def __init__(self) -> None:
        self._client = None
        self._collection = None
        self._embeddings = None
        self._supabase_client = None

    @property
    def embeddings(self) -> GoogleGenerativeAIEmbeddings:
        if self._embeddings is None:
            if not settings.gemini_api_key:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Gemini API key is missing.",
                )

            self._embeddings = GoogleGenerativeAIEmbeddings(
                model=EMBEDDING_MODEL,
                google_api_key=settings.gemini_api_key,
            )

        return self._embeddings

    @property
    def collection(self):
        if self._collection is None:
            if not VECTOR_DB_DIR.exists():
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Scheme vector database has not been built.",
                )

            self._client = chromadb.PersistentClient(path=str(VECTOR_DB_DIR))

            try:
                self._collection = self._client.get_collection(COLLECTION_NAME)
            except Exception as exc:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Scheme vector collection was not found.",
                ) from exc

        return self._collection

    @property
    def supabase_client(self):
        if self._supabase_client is None:
            supabase_key = settings.supabase_service_role_key or settings.supabase_anon_key

            if not settings.supabase_url or not supabase_key:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Supabase configuration is missing.",
                )

            self._supabase_client = create_client(settings.supabase_url, supabase_key)

        return self._supabase_client

    def retrieve_sources(
        self,
        question: str,
        limit: int = 5,
        fetch_k: int = 20,
        search_type: str = "mmr",
    ) -> list[dict[str, Any]]:
        cleaned_question = question.strip()
        if not cleaned_question:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Question is required.",
            )

        try:
            query_embedding = self.embeddings.embed_query(cleaned_question)
        except Exception as exc:
            if _is_gemini_quota_or_api_error(exc):
                raise GeminiQuotaExceededError from exc
            raise

        n_results = max(limit, fetch_k if search_type == "mmr" else limit)
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            include=["documents", "metadatas", "distances", "embeddings"],
        )

        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]
        embeddings = results.get("embeddings", [[]])[0]

        sources: list[dict[str, Any]] = []
        for index, (document, metadata, distance) in enumerate(zip(documents, metadatas, distances)):
            sources.append(
                {
                    "type": "scheme",
                    "scheme_id": metadata.get("scheme_id", ""),
                    "title": metadata.get("title", ""),
                    "category": metadata.get("category", ""),
                    "state": metadata.get("state", ""),
                    "application_link": metadata.get("application_link", ""),
                    "url": metadata.get("application_link", ""),
                    "snippet": document,
                    "distance": distance,
                    "embedding": embeddings[index] if index < len(embeddings) else None,
                }
            )

        if search_type != "mmr" or len(sources) <= limit:
            return self._strip_internal_source_fields(sources[:limit])

        selected = self._select_mmr_sources(query_embedding, sources, limit=limit)
        return self._strip_internal_source_fields(selected)

    def answer_question(self, question: str) -> dict[str, Any]:
        sources = self.retrieve_sources(question)

        if not sources:
            return {
                "answer": "I could not find matching government schemes for that question.",
                "sources": [],
            }

        context = "\n\n".join(
            (
                f"Title: {source['title']}\n"
                f"Category: {source['category']}\n"
                f"State: {source['state']}\n"
                f"Application link: {source['application_link']}\n"
                f"Details: {source['snippet']}"
            )
            for source in sources
        )

        model = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=settings.gemini_api_key,
            temperature=0.2,
        )

        prompt = (
            "Answer the user's question using only the scheme context below. "
            "If the context does not contain the answer, say you do not know. "
            "Keep the answer concise and mention relevant scheme names.\n\n"
            f"Question: {question}\n\n"
            f"Scheme context:\n{context}"
        )

        try:
            response = model.invoke(prompt)
        except Exception as exc:
            if _is_gemini_quota_or_api_error(exc):
                raise GeminiQuotaExceededError from exc
            raise

        answer = (
            response.content
            if isinstance(response.content, str)
            else str(response.content)
        )

        return {
            "answer": answer,
            "sources": sources,
        }

    def answer_personalized_question(
        self,
        access_token: str,
        question: str,
        history: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        user_id = self._get_authenticated_user_id(access_token)
        profile = self._fetch_profile(user_id)
        profile_context = self._build_profile_context(profile)
        history_context = self._build_history_context(history or [])
        retrieval_query = self._build_retrieval_query(question, history or [], profile)
        sources = self.retrieve_sources(retrieval_query, limit=5, fetch_k=20, search_type="mmr")
        sources = self._filter_retrieved_sources_for_question(question, sources, history or [])
        used_web_search = self.should_use_web_search(question)
        web_results = (
            web_search_service.search_official_sources(retrieval_query, limit=3)
            if used_web_search
            else []
        )
        if not sources and not used_web_search:
            return {
                "answer": INSUFFICIENT_RELEVANCE_RESPONSE,
                "sources": [],
                "action_links": [],
                "follow_ups": self._generate_follow_ups(question, INSUFFICIENT_RELEVANCE_RESPONSE, []),
                "used_profile": bool(profile),
                "used_web_search": used_web_search,
            }
        portal_issue_state = self._official_page_issue_state(web_results)
        if used_web_search and portal_issue_state:
            response_sources = self._dynamic_portal_issue_sources(web_results, sources)
            return {
                "answer": DYNAMIC_PORTAL_PLACEHOLDER_RESPONSE,
                "sources": response_sources,
                "action_links": self._generate_action_links(question, response_sources),
                "follow_ups": self._generate_follow_ups(
                    question,
                    DYNAMIC_PORTAL_PLACEHOLDER_RESPONSE,
                    response_sources,
                ),
                "used_profile": bool(profile),
                "used_web_search": used_web_search,
            }
        if used_web_search and not self._has_verified_web_content(web_results):
            response_sources = self._dynamic_unverified_sources(question, sources)
            return {
                "answer": DYNAMIC_UNVERIFIED_RESPONSE,
                "sources": response_sources,
                "action_links": self._generate_action_links(question, response_sources),
                "follow_ups": self._generate_follow_ups(
                    question,
                    DYNAMIC_UNVERIFIED_RESPONSE,
                    response_sources,
                ),
                "used_profile": bool(profile),
                "used_web_search": used_web_search,
            }

        prompt = self._build_personalized_prompt(
            question=question,
            profile_context=profile_context,
            history_context=history_context,
            sources=sources,
            web_results=web_results,
        )

        model = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=settings.gemini_api_key,
            temperature=0.2,
        )

        try:
            response = model.invoke(prompt)
        except Exception as exc:
            if _is_gemini_quota_or_api_error(exc):
                raise GeminiQuotaExceededError from exc
            raise

        answer = response.content if isinstance(response.content, str) else str(response.content)
        response_sources = self._filter_response_sources(
            question,
            answer,
            [*sources, *web_results],
        )
        return {
            "answer": answer,
            "sources": response_sources,
            "action_links": self._generate_action_links(question, response_sources),
            "follow_ups": self._generate_follow_ups(question, answer, response_sources),
            "used_profile": bool(profile),
            "used_web_search": used_web_search,
        }

    def should_use_web_search(self, question: str) -> bool:
        normalized_question = question.lower()
        return any(keyword in normalized_question for keyword in RECENT_UPDATE_KEYWORDS)

    def _get_authenticated_user_id(self, access_token: str) -> str:
        try:
            response = self.supabase_client.auth.get_user(access_token)
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

    def _fetch_profile(self, user_id: str) -> dict[str, Any]:
        response = (
            self.supabase_client.table("profiles")
            .select(PROFILE_FIELDS)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )

        return (response.data or [{}])[0]

    def _build_profile_context(self, profile: dict[str, Any]) -> str:
        if not profile:
            return "No completed profile was found. Do not assume personal details."

        lines = []
        field_labels = {
            "age": "Age",
            "gender": "Gender",
            "state": "State",
            "occupation": "Occupation",
            "education_level": "Education",
            "annual_family_income": "Annual family income",
            "category": "Category",
            "disability_status": "Disability information",
            "minority_status": "Minority status",
        }
        for field, label in field_labels.items():
            value = profile.get(field)
            if value is not None and value != "":
                lines.append(f"{label}: {value}")

        return "\n".join(lines) if lines else "Profile exists but has no usable details."

    def _build_history_context(self, history: list[dict[str, Any]]) -> str:
        if not history:
            return "No recent conversation in this session."

        recent_messages = history[-10:]
        lines = []
        for message in recent_messages:
            role = str(message.get("role") or "message").title()
            content = str(message.get("content") or "").strip()
            if content:
                lines.append(f"{role}: {content}")

        return "\n".join(lines) if lines else "No recent conversation in this session."

    def _build_retrieval_query(
        self,
        question: str,
        history: list[dict[str, Any]],
        profile: dict[str, Any],
    ) -> str:
        previous_context = " ".join(
            str(message.get("content") or "")
            for message in history[-4:]
            if message.get("content")
        )
        profile_terms = " ".join(
            str(profile.get(field) or "")
            for field in ("state", "occupation", "education_level", "category", "gender")
        )
        return " ".join(part for part in [previous_context, question, profile_terms] if part).strip()

    def _build_personalized_prompt(
        self,
        question: str,
        profile_context: str,
        history_context: str,
        sources: list[dict[str, Any]],
        web_results: list[dict[str, Any]],
    ) -> str:
        scheme_context = self._format_scheme_context(sources)
        web_context = self._format_web_context(web_results)

        return (
            "System Instructions\n"
            "You are a government schemes assistant. Do not use greetings, small talk, or conversational openings. "
            "Do not start with phrases like Hello, Hi, As a student, or Based on your profile. "
            "Answer directly and concisely using plain text section labels only: Answer, Key Details, Eligibility, Next Steps, Official Source. "
            "Do not wrap section labels in markdown markers such as **. Use mostly bullet points. Keep each section to at most 5 short bullets. Omit irrelevant sections. "
            "Mention profile information only when it materially changes the answer. "
            "Use the user profile only for relevance, and only use the information in the sections below. "
            "Do not invent schemes, eligibility, deadlines, application status, or dates. "
            "Do not make generic assumptions such as generally required documents unless those details exist in retrieved scheme chunks or verified official web content. "
            "If the provided information is insufficient, say so clearly. Prefer official information. "
            "For dynamic questions about deadlines, latest notifications, or whether applications are open, answer only from extracted official web content. "
            "If official content does not verify the deadline/status, explain why verification was not possible and give next steps to check the official portal. "
            "Mention official source names when useful, but do not print raw URLs in the answer text because action links are rendered separately.\n\n"
            "User Profile\n"
            f"{profile_context}\n\n"
            "Recent Conversation\n"
            f"{history_context}\n\n"
            "Retrieved Scheme Information\n"
            f"{scheme_context}\n\n"
            "Verified Web Information\n"
            f"{web_context}\n\n"
            "Current User Question\n"
            f"{question}"
        )

    def _format_scheme_context(self, sources: list[dict[str, Any]]) -> str:
        if not sources:
            return "No matching scheme chunks were retrieved."

        return "\n\n".join(
            (
                f"Source {index + 1}: {source.get('title') or 'Untitled scheme'}\n"
                f"Category: {source.get('category') or 'Not specified'}\n"
                f"State: {source.get('state') or 'All India'}\n"
                f"URL: {source.get('application_link') or source.get('url') or 'Not available'}\n"
                f"Details: {source.get('snippet') or ''}"
            )
            for index, source in enumerate(sources)
        )

    def _format_web_context(self, web_results: list[dict[str, Any]]) -> str:
        if not web_results:
            return "Web verification was not needed for this question."

        return "\n\n".join(
            (
                f"Web source {index + 1}: {result.get('title') or 'Official source'}\n"
                f"URL: {result.get('url') or 'Not available'}\n"
                f"Verified: {result.get('verified')}\n"
                f"Snippet: {result.get('snippet') or ''}\n"
                f"Extracted official content: {result.get('content') or result.get('snippet') or ''}"
            )
            for index, result in enumerate(web_results)
        )

    def _filter_response_sources(
        self,
        question: str,
        answer: str,
        sources: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        seen_keys = set()
        visible_sources = []
        query_terms = self._important_terms(f"{question} {answer}")

        for source in sources:
            if self._is_internal_source(source):
                continue

            key = (
                source.get("scheme_id")
                or source.get("url")
                or source.get("application_link")
                or source.get("title")
            )
            if not key or key in seen_keys:
                continue
            seen_keys.add(key)
            visible_sources.append(source)

        ranked_sources = sorted(
            visible_sources,
            key=lambda source: self._source_relevance_score(source, query_terms),
            reverse=True,
        )
        relevant_sources = [
            source
            for source in ranked_sources
            if source.get("type") == "web"
            or self._source_relevance_score(source, query_terms) > 0
        ]
        limit = 2 if self._should_suppress_cards(question) else MAX_RESPONSE_SOURCES
        return relevant_sources[:limit]

    def _filter_retrieved_sources_for_question(
        self,
        question: str,
        sources: list[dict[str, Any]],
        history: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if not sources:
            return []

        topic_terms = self._topic_terms_for_relevance(question, history)
        if not topic_terms:
            return sources

        filtered_sources = [
            source
            for source in sources
            if self._source_matches_topic(source, topic_terms)
        ]
        return filtered_sources

    def _topic_terms_for_relevance(
        self,
        question: str,
        history: list[dict[str, Any]],
    ) -> set[str]:
        recent_context = " ".join(
            str(message.get("content") or "")
            for message in history[-4:]
            if message.get("content")
        )
        terms = self._important_terms(f"{recent_context} {question}")
        generic_terms = {
            "find",
            "show",
            "tell",
            "about",
            "scheme",
            "schemes",
            "government",
            "families",
            "family",
            "income",
            "low",
            "poor",
            "beneficiary",
            "beneficiaries",
            "details",
            "required",
            "documents",
            "apply",
            "eligible",
            "eligibility",
        }
        topic_terms = {term for term in terms if term not in generic_terms}
        if "business" in topic_terms or "start" in topic_terms:
            topic_terms.update({"entrepreneur", "entrepreneurs", "entrepreneurship", "startup"})
        if "health" in topic_terms:
            topic_terms.update({"medical", "healthcare", "insurance", "ayushman"})

        return topic_terms

    def _source_matches_topic(self, source: dict[str, Any], topic_terms: set[str]) -> bool:
        haystack = " ".join(
            str(source.get(field) or "")
            for field in ("title", "category", "state", "snippet", "content")
        ).lower()
        return any(term in haystack for term in topic_terms)

    def _has_verified_web_content(self, web_results: list[dict[str, Any]]) -> bool:
        for result in web_results:
            if self._is_internal_source(result):
                continue

            content = str(result.get("content") or result.get("snippet") or "").strip()
            page_state = result.get("official_page_state") or "verified"
            if (
                result.get("verified") is True
                and page_state == "verified"
                and content
                and "could not verify this information" not in content.lower()
            ):
                return True

        return False

    def _official_page_issue_state(self, web_results: list[dict[str, Any]]) -> str:
        for result in web_results:
            state = result.get("official_page_state")
            if state in {"placeholder", "maintenance"} and result.get("url"):
                return str(state)

        return ""

    def _dynamic_portal_issue_sources(
        self,
        web_results: list[dict[str, Any]],
        scheme_sources: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        for result in web_results:
            state = result.get("official_page_state")
            if state in {"placeholder", "maintenance"} and result.get("url"):
                return [
                    {
                        "type": "web",
                        "title": result.get("title") or "Official Portal",
                        "url": result.get("url"),
                        "snippet": "The official portal did not expose the requested information in extracted text.",
                        "verified": False,
                        "official_page_state": state,
                    }
                ]

        portal_source = self._build_portal_source(scheme_sources[0] if scheme_sources else None)
        return [portal_source] if portal_source else []

    def _dynamic_unverified_sources(
        self,
        question: str,
        sources: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        query_terms = self._important_terms(question)
        ranked_scheme_sources = sorted(
            [
                source
                for source in sources
                if source.get("type") == "scheme" and not self._is_internal_source(source)
            ],
            key=lambda source: self._source_relevance_score(source, query_terms),
            reverse=True,
        )

        selected_sources = []
        if ranked_scheme_sources:
            selected_sources.append(ranked_scheme_sources[0])

        portal_source = self._build_portal_source(selected_sources[0] if selected_sources else None)
        if portal_source:
            selected_sources.append(portal_source)

        return self._dedupe_sources(selected_sources)[:2]

    def _should_suppress_cards(self, question: str) -> bool:
        normalized_question = question.lower()
        procedural_terms = (
            "deadline",
            "last date",
            "renew",
            "renewal",
            "application status",
            "currently open",
            "latest notification",
            "notification",
            "documents",
            "required",
            "how do i",
            "how to",
            "eligible",
            "eligibility",
        )
        return any(term in normalized_question for term in procedural_terms)

    def _generate_action_links(
        self,
        question: str,
        sources: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        links = []
        normalized_question = question.lower()

        for source in sources:
            url = source.get("url") or source.get("application_link")
            if not url:
                continue

            links.append(
                {
                    "label": self._action_label(normalized_question, source),
                    "url": url,
                    "is_official": source.get("type") == "web" or bool(source.get("application_link")),
                }
            )

        return self._dedupe_action_links(links)[:3]

    def _action_label(self, question: str, source: dict[str, Any]) -> str:
        url = str(source.get("url") or source.get("application_link") or "").lower()
        title = str(source.get("title") or "").lower()

        if url.endswith(".pdf"):
            return "Download Notification PDF"
        if source.get("official_page_state") in {"placeholder", "maintenance"}:
            return "Open Official Portal"
        if "renew" in question and ("nsp" in question or "scholarship" in question):
            return "Renew on NSP"
        if "status" in question:
            return "View Application Status"
        if "notification" in question or "deadline" in question or "last date" in question or "currently" in question:
            return "Check Latest Notifications"
        if "guideline" in title:
            return "View Official Guidelines"
        if "apply" in question:
            return "Apply Here"

        return "Open Official Portal"

    def _dedupe_action_links(self, links: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen_urls = set()
        deduped_links = []
        for link in links:
            url = link.get("url")
            normalized_url = self._normalize_url(url)
            if not normalized_url or normalized_url in seen_urls:
                continue
            seen_urls.add(normalized_url)
            deduped_links.append(link)

        return deduped_links

    def _normalize_url(self, url: Any) -> str:
        return str(url or "").strip().rstrip("/").lower()

    def _build_portal_source(self, source: dict[str, Any] | None) -> dict[str, Any] | None:
        if not source:
            return None

        url = source.get("application_link") or source.get("url")
        if not url:
            return None

        return {
            "type": "web",
            "title": "Official Portal",
            "url": url,
            "snippet": "Check the official portal notifications section for the latest updates.",
            "verified": True,
        }

    def _dedupe_sources(self, sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen_keys = set()
        deduped_sources = []
        for source in sources:
            key = (
                source.get("scheme_id")
                or source.get("url")
                or source.get("application_link")
                or source.get("title")
            )
            if not key or key in seen_keys:
                continue

            seen_keys.add(key)
            deduped_sources.append(source)

        return deduped_sources

    def _is_internal_source(self, source: dict[str, Any]) -> bool:
        return (
            source.get("verified") is False
            or source.get("title") == INTERNAL_WEB_FALLBACK_TITLE
        )

    def _source_relevance_score(
        self,
        source: dict[str, Any],
        query_terms: set[str],
    ) -> int:
        haystack = " ".join(
            str(source.get(field) or "")
            for field in ("title", "category", "state", "snippet", "content")
        ).lower()
        score = sum(1 for term in query_terms if term in haystack)

        if source.get("type") == "web" and source.get("verified") is True:
            score += 3
        if source.get("title") and str(source["title"]).lower() in haystack:
            score += 1

        return score

    def _important_terms(self, text: str) -> set[str]:
        stop_words = {
            "what",
            "when",
            "where",
            "which",
            "under",
            "for",
            "the",
            "and",
            "are",
            "is",
            "currently",
            "latest",
            "last",
            "date",
            "deadline",
            "application",
            "applications",
            "open",
        }
        terms = {
            term
            for term in re.findall(r"[a-z0-9]+", text.lower())
            if len(term) > 2 and term not in stop_words
        }

        aliases = set()
        if "nsp" in terms:
            aliases.update({"national", "scholarship", "portal", "central", "sector"})
        if "pmegp" in terms:
            aliases.update({"prime", "minister", "employment", "generation"})
        if "pmay" in terms:
            aliases.update({"awas", "yojana", "housing"})
        if "vishwakarma" in terms:
            aliases.update({"pm", "vishwakarma"})

        return terms | aliases

    def _generate_follow_ups(
        self,
        question: str,
        answer: str,
        sources: list[dict[str, Any]],
    ) -> list[str]:
        text = f"{question} {answer} {' '.join(str(source.get('title') or '') for source in sources)}".lower()

        if "renew" in text or "renewal" in text:
            return [
                "Renewal eligibility",
                "Required documents",
                "How to renew on NSP",
                "Latest NSP notifications",
            ]

        if "deadline" in text or "last date" in text or "currently" in text or "notification" in text:
            return [
                "Eligibility details",
                "Required documents",
                "How to apply",
                "Latest official updates",
            ]

        if "pmegp" in text or "business" in text or "entrepreneur" in text:
            return [
                "PMEGP eligibility",
                "Required documents",
                "How to apply for PMEGP",
                "Current PMEGP status",
            ]

        if "health" in text or "medical" in text or "healthcare" in text or "ayushman" in text:
            return [
                "Eligibility",
                "State-specific schemes",
                "Required documents",
                "Application process",
            ]

        if "scholarship" in text or "student" in text:
            return [
                "Scholarship eligibility",
                "Required documents",
                "How to apply",
                "Renewal process",
            ]

        return [
            "Eligibility details",
            "Required documents",
            "How to apply",
            "Official updates",
        ]

    def _select_mmr_sources(
        self,
        query_embedding: list[float],
        sources: list[dict[str, Any]],
        limit: int,
        lambda_mult: float = 0.5,
    ) -> list[dict[str, Any]]:
        candidates = [
            source
            for source in sources
            if self._normalize_embedding(source.get("embedding"))
        ]
        if len(candidates) < limit:
            return sources[:limit]

        selected: list[dict[str, Any]] = []
        remaining = candidates.copy()
        while remaining and len(selected) < limit:
            best_source = max(
                remaining,
                key=lambda source: self._mmr_score(
                    query_embedding,
                    source,
                    selected,
                    lambda_mult=lambda_mult,
                ),
            )
            selected.append(best_source)
            remaining.remove(best_source)

        return selected

    def _mmr_score(
        self,
        query_embedding: list[float],
        source: dict[str, Any],
        selected: list[dict[str, Any]],
        lambda_mult: float,
    ) -> float:
        source_embedding = self._normalize_embedding(source.get("embedding"))
        relevance = self._cosine_similarity(query_embedding, source_embedding)
        diversity_penalty = max(
            (
                self._cosine_similarity(
                    source_embedding,
                    self._normalize_embedding(selected_source.get("embedding")),
                )
                for selected_source in selected
            ),
            default=0.0,
        )
        return (lambda_mult * relevance) - ((1 - lambda_mult) * diversity_penalty)

    def _cosine_similarity(self, first: Any, second: Any) -> float:
        first_embedding = self._normalize_embedding(first)
        second_embedding = self._normalize_embedding(second)

        if len(first_embedding) == 0 or len(second_embedding) == 0:
            return 0.0

        dot_product = sum(a * b for a, b in zip(first_embedding, second_embedding))
        first_norm = math.sqrt(sum(a * a for a in first_embedding))
        second_norm = math.sqrt(sum(b * b for b in second_embedding))
        if first_norm == 0 or second_norm == 0:
            return 0.0

        return dot_product / (first_norm * second_norm)

    def _normalize_embedding(self, embedding: Any) -> list[float]:
        if embedding is None:
            return []

        if hasattr(embedding, "tolist"):
            embedding = embedding.tolist()

        if isinstance(embedding, tuple):
            embedding = list(embedding)

        if not isinstance(embedding, list):
            return []

        if len(embedding) == 0:
            return []

        return [float(value) for value in embedding]

    def _strip_internal_source_fields(
        self,
        sources: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        cleaned_sources = []
        for source in sources:
            cleaned_source = dict(source)
            cleaned_source.pop("embedding", None)
            cleaned_sources.append(cleaned_source)

        return cleaned_sources


chatbot_service = ChatbotService()
