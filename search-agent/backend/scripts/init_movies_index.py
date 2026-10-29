#!/usr/bin/env python3
"""映画インデックスを初期化するスクリプト"""

import argparse
import csv
import json
import re
import sys
from pathlib import Path

sys.path.append("/app")

from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk

ELASTICSEARCH_HOST = "http://elasticsearch:9200"
INDEX_NAME = "movies"
DATA_PATH = "/data/tmdb_movies_50k.csv"
MAPPING_PATH = Path(__file__).parent / "movies_index_mapping.json"


def load_mapping() -> dict:
    """JSONファイルからマッピング定義を読み込む"""
    with open(MAPPING_PATH, encoding="utf-8") as f:
        return json.load(f)


def create_index(es: Elasticsearch, force_recreate: bool = False) -> bool:
    if es.indices.exists(index=INDEX_NAME):
        if force_recreate:
            print(f"Deleting existing index: {INDEX_NAME}")
            es.indices.delete(index=INDEX_NAME)
        else:
            print(f"Index {INDEX_NAME} already exists. Use --force-recreate to recreate.")
            return False

    print(f"Creating index: {INDEX_NAME}")
    mappings = load_mapping()
    es.indices.create(index=INDEX_NAME, mappings=mappings)
    return True


def parse_list_field(value: str) -> list[str]:
    """カンマ区切りの文字列をリストに変換"""
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def validate_release_date(date_str: str) -> str | None:
    """release_dateのバリデーション（yyyy-MM-dd形式のみ許可）"""
    if not date_str:
        return None
    if re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        return date_str
    if re.match(r"^\d{4}$", date_str):
        return date_str
    return None


def safe_int(value: str, default: int = 0) -> int:
    """文字列を安全にintに変換"""
    try:
        return int(float(value)) if value else default
    except (ValueError, TypeError):
        return default


def safe_float(value: str, default: float = 0.0) -> float:
    """文字列を安全にfloatに変換"""
    try:
        return float(value) if value else default
    except (ValueError, TypeError):
        return default


def parse_row(row: dict) -> dict:
    """CSVの1行をElasticsearchドキュメントに変換"""
    doc = {
        "id": row.get("id", ""),
        "title": row.get("title", ""),
        "original_title": row.get("original_title", ""),
        "overview": row.get("overview", ""),
        "tagline": row.get("tagline", ""),
        "genres": parse_list_field(row.get("genres", "")),
        "keywords": parse_list_field(row.get("keywords", "")),
        "popularity": safe_float(row.get("popularity")),
        "vote_average": safe_float(row.get("vote_average")),
        "vote_count": safe_int(row.get("vote_count")),
        "runtime": safe_int(row.get("runtime")),
        "budget": safe_int(row.get("budget")),
        "revenue": safe_int(row.get("revenue")),
    }

    release_date = validate_release_date(row.get("release_date", ""))
    if release_date:
        doc["release_date"] = release_date

    optional_fields = [
        "status",
        "homepage",
        "imdb_id",
        "original_language",
        "poster_path",
        "backdrop_path",
    ]
    for field in optional_fields:
        value = row.get(field, "")
        if value:
            doc[field] = value

    adult_str = row.get("adult", "").lower()
    if adult_str in ("true", "false"):
        doc["adult"] = adult_str == "true"

    list_fields = ["production_companies", "production_countries", "spoken_languages"]
    for field in list_fields:
        values = parse_list_field(row.get(field, ""))
        if values:
            doc[field] = values

    return doc


def load_movies(es: Elasticsearch, data_path: str):
    print(f"Loading movies from: {data_path}")

    with open(data_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        documents = []

        for row in reader:
            doc = parse_row(row)
            if not doc["id"]:
                continue

            documents.append({"_index": INDEX_NAME, "_id": doc["id"], "_source": doc})

            if len(documents) >= 500:
                bulk(es, documents)
                print(f"Indexed {len(documents)} documents...")
                documents = []

        if documents:
            bulk(es, documents)
            print(f"Indexed {len(documents)} documents...")

    count = es.count(index=INDEX_NAME)["count"]
    print(f"Total documents indexed: {count}")


def main():
    parser = argparse.ArgumentParser(description="Initialize movies index")
    parser.add_argument(
        "--force-recreate",
        action="store_true",
        help="Force recreate the index if it exists",
    )
    args = parser.parse_args()

    es = Elasticsearch([ELASTICSEARCH_HOST], verify_certs=False)

    if not es.ping():
        print("Failed to connect to Elasticsearch")
        sys.exit(1)

    print("Connected to Elasticsearch")

    if create_index(es, args.force_recreate):
        load_movies(es, DATA_PATH)
    else:
        print("Skipping data load. Use --force-recreate to reload data.")


if __name__ == "__main__":
    main()
