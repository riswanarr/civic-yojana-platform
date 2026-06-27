from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path
from typing import Any

from dotenv import dotenv_values
from supabase import create_client


BACKEND_DIR = Path(__file__).resolve().parents[1]
DATASET_PATH = BACKEND_DIR / "app" / "data" / "schemes.txt"
ENV_PATH = BACKEND_DIR / ".env"

REQUIRED_FIELDS = (
    "SCHEME",
    "CATEGORY",
    "ELIGIBILITY",
    "BENEFITS",
    "DOCUMENTS",
    "DEADLINE",
    "APPLY AT",
    "STATES",
)

URL_PATTERN = re.compile(r"https?://[^\s,]+")
TAG_WORD_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9+-]*")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import government opportunities from app/data/schemes.txt.",
    )
    parser.add_argument(
        "--insert",
        action="store_true",
        help="Insert new records. Omit this flag for a dry run.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the dry-run/import summary as JSON.",
    )
    return parser.parse_args()


def parse_dataset(path: Path = DATASET_PATH) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    blocks = [block.strip() for block in re.split(r"\n\s*\n", text) if block.strip()]
    records: list[dict[str, Any]] = []

    for index, block in enumerate(blocks, start=1):
        raw_fields: dict[str, str] = {}

        for line in block.splitlines():
            if ":" not in line:
                raise ValueError(f"Record {index} has an invalid line: {line}")

            key, value = line.split(":", 1)
            raw_fields[key.strip()] = value.strip()

        missing_fields = [field for field in REQUIRED_FIELDS if not raw_fields.get(field)]
        if missing_fields:
            missing = ", ".join(missing_fields)
            raise ValueError(f"Record {index} is missing required field(s): {missing}")

        records.append(build_scheme_record(raw_fields))

    return records


def build_scheme_record(raw_fields: dict[str, str]) -> dict[str, Any]:
    title = raw_fields["SCHEME"]
    category = raw_fields["CATEGORY"]
    state = raw_fields["STATES"] or "All India"
    apply_at = raw_fields["APPLY AT"]
    application_link = extract_first_url(apply_at)

    return {
        "title": title,
        "description": build_description(title, category, state),
        "ministry": None,
        "state": state,
        "category": category,
        "eligibility_criteria": raw_fields["ELIGIBILITY"],
        "benefits": raw_fields["BENEFITS"],
        "application_link": application_link,
        "official_source": application_link,
        "deadline": parse_iso_date(raw_fields["DEADLINE"]),
        "tags": build_tags(title, category, state),
    }


def build_description(title: str, category: str, state: str) -> str:
    if state == "All India":
        return f"{title} is a government opportunity in the {category} category."

    return f"{title} is a government opportunity in the {category} category for {state}."


def extract_first_url(value: str) -> str | None:
    match = URL_PATTERN.search(value)
    return match.group(0).rstrip(".") if match else None


def parse_iso_date(value: str) -> str | None:
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        return None


def build_tags(title: str, category: str, state: str) -> list[str]:
    tags: list[str] = []

    for source in (category, state, title):
        for word in TAG_WORD_PATTERN.findall(source.lower()):
            normalized = word.strip("-+")
            if len(normalized) < 3:
                continue
            if normalized not in tags:
                tags.append(normalized)
            if len(tags) >= 12:
                return tags

    return tags


def load_supabase_client():
    env = dotenv_values(ENV_PATH)
    supabase_url = env.get("SUPABASE_URL")
    supabase_key = env.get("SUPABASE_SERVICE_ROLE_KEY") or env.get("SUPABASE_ANON_KEY")

    if not supabase_url or not supabase_key:
        raise RuntimeError("Supabase configuration is missing in backend/.env.")

    return create_client(supabase_url, supabase_key)


def find_duplicate_titles(records: list[dict[str, Any]]) -> list[str]:
    seen: set[str] = set()
    duplicates: list[str] = []

    for record in records:
        normalized_title = normalize_title(record["title"])
        if normalized_title in seen and record["title"] not in duplicates:
            duplicates.append(record["title"])
        seen.add(normalized_title)

    return duplicates


def fetch_existing_titles(client) -> set[str]:
    response = client.table("schemes").select("title").execute()
    return {
        normalize_title(row["title"])
        for row in (response.data or [])
        if row.get("title")
    }


def normalize_title(title: str) -> str:
    return " ".join(title.casefold().split())


def summarize(records: list[dict[str, Any]], existing_titles: set[str]) -> dict[str, Any]:
    duplicate_titles = find_duplicate_titles(records)
    insertable_records = [
        record
        for record in records
        if normalize_title(record["title"]) not in existing_titles
    ]

    return {
        "parsed_schemes": len(records),
        "sample_parsed_record": records[0] if records else None,
        "duplicate_titles": len(duplicate_titles),
        "duplicate_title_values": duplicate_titles,
        "existing_title_matches": len(records) - len(insertable_records),
        "rows_that_would_be_inserted": len(insertable_records),
    }


def insert_records(records: list[dict[str, Any]], existing_titles: set[str]) -> int:
    insertable_records = [
        record
        for record in records
        if normalize_title(record["title"]) not in existing_titles
    ]

    if not insertable_records:
        return 0

    client = load_supabase_client()
    client.table("schemes").insert(insertable_records).execute()
    return len(insertable_records)


def print_summary(summary: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(summary, indent=2))
        return

    print(f"Parsed schemes: {summary['parsed_schemes']}")
    print(f"Duplicate titles in dataset: {summary['duplicate_titles']}")
    print(f"Existing title matches: {summary['existing_title_matches']}")
    print(f"Rows that would be inserted: {summary['rows_that_would_be_inserted']}")
    print("Sample parsed record:")
    print(json.dumps(summary["sample_parsed_record"], indent=2))


def main() -> None:
    args = parse_args()
    records = parse_dataset()
    client = load_supabase_client()
    existing_titles = fetch_existing_titles(client)
    summary = summarize(records, existing_titles)

    if args.insert:
        summary["inserted_rows"] = insert_records(records, existing_titles)
    else:
        summary["inserted_rows"] = 0

    print_summary(summary, args.json)


if __name__ == "__main__":
    main()
