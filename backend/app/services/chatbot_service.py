from __future__ import annotations

from pathlib import Path
from typing import Any

import chromadb
from fastapi import HTTPException, status
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

from app.config import settings


BACKEND_DIR = Path(__file__).resolve().parents[2]
VECTOR_DB_DIR = BACKEND_DIR / "app" / "data" / "chroma_schemes"
COLLECTION_NAME = "schemes"
EMBEDDING_MODEL = "models/gemini-embedding-001"
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

    def retrieve_sources(self, question: str, limit: int = 5) -> list[dict[str, Any]]:
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

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=limit,
            include=["documents", "metadatas", "distances"],
        )

        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        sources: list[dict[str, Any]] = []
        for document, metadata, distance in zip(documents, metadatas, distances):
            sources.append(
                {
                    "scheme_id": metadata.get("scheme_id", ""),
                    "title": metadata.get("title", ""),
                    "category": metadata.get("category", ""),
                    "state": metadata.get("state", ""),
                    "application_link": metadata.get("application_link", ""),
                    "snippet": document,
                    "distance": distance,
                }
            )

        return sources

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


chatbot_service = ChatbotService()
