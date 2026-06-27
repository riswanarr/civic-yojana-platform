from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import chromadb
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from supabase import create_client


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.config import settings  # noqa: E402
from app.services.chatbot_service import (  # noqa: E402
    COLLECTION_NAME,
    EMBEDDING_MODEL,
    VECTOR_DB_DIR,
)


SCHEME_COLUMNS = (
    "id,title,description,ministry,state,category,eligibility_criteria,"
    "benefits,application_link,official_source"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the local ChromaDB index for scheme chatbot retrieval.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the build summary as JSON.",
    )
    return parser.parse_args()


def load_supabase_client():
    supabase_key = settings.supabase_service_role_key or settings.supabase_anon_key

    if not settings.supabase_url or not supabase_key:
        raise RuntimeError("Supabase configuration is missing.")

    return create_client(settings.supabase_url, supabase_key)


def fetch_schemes() -> list[dict[str, Any]]:
    response = (
        load_supabase_client()
        .table("schemes")
        .select(SCHEME_COLUMNS)
        .order("created_at", desc=False)
        .execute()
    )
    return response.data or []


def build_document(scheme: dict[str, Any]) -> Document:
    page_content = "\n".join(
        [
            f"Title: {scheme.get('title') or ''}",
            f"Category: {scheme.get('category') or ''}",
            f"State: {scheme.get('state') or ''}",
            f"Description: {scheme.get('description') or ''}",
            f"Eligibility: {scheme.get('eligibility_criteria') or ''}",
            f"Benefits: {scheme.get('benefits') or ''}",
            f"Ministry: {scheme.get('ministry') or ''}",
            f"Official source: {scheme.get('official_source') or ''}",
            f"Application link: {scheme.get('application_link') or ''}",
        ]
    )

    return Document(
        page_content=page_content,
        metadata={
            "scheme_id": str(scheme.get("id") or ""),
            "title": str(scheme.get("title") or ""),
            "category": str(scheme.get("category") or ""),
            "state": str(scheme.get("state") or ""),
            "application_link": str(scheme.get("application_link") or ""),
        },
    )


def recreate_collection(documents: list[Document]) -> int:
    if not settings.gemini_api_key:
        raise RuntimeError("Gemini API key is missing.")

    VECTOR_DB_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(VECTOR_DB_DIR))

    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass

    collection = client.create_collection(COLLECTION_NAME)
    embeddings = GoogleGenerativeAIEmbeddings(
        model=EMBEDDING_MODEL,
        google_api_key=settings.gemini_api_key,
    )

    texts = [document.page_content for document in documents]
    vectors = embeddings.embed_documents(texts)

    collection.add(
        ids=[document.metadata["scheme_id"] for document in documents],
        documents=texts,
        metadatas=[document.metadata for document in documents],
        embeddings=vectors,
    )

    return collection.count()


def print_summary(summary: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(summary, indent=2))
        return

    print(f"Fetched schemes: {summary['fetched_schemes']}")
    print(f"Embedded documents: {summary['embedded_documents']}")
    print(f"Vector DB location: {summary['vector_db_location']}")


def main() -> None:
    args = parse_args()
    schemes = fetch_schemes()
    documents = [build_document(scheme) for scheme in schemes]
    embedded_documents = recreate_collection(documents)

    print_summary(
        {
            "fetched_schemes": len(schemes),
            "embedded_documents": embedded_documents,
            "vector_db_location": str(VECTOR_DB_DIR),
            "collection": COLLECTION_NAME,
        },
        args.json,
    )


if __name__ == "__main__":
    main()
