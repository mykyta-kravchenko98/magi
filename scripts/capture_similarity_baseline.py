"""Capture filtered Qdrant similarity results for a fixed query suite."""

import argparse
import asyncio
import json
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import cast
from uuid import UUID

import httpx

from magi.ingestion.infrastructure.embedding import TeiEmbeddingConfig, TeiEmbeddingProvider
from magi.shared.config import EmbeddingSettings, QdrantSettings


@dataclass(frozen=True, slots=True, kw_only=True)
class QueryCase:
    query_id: str
    text: str
    purpose: str


@dataclass(frozen=True, slots=True, kw_only=True)
class QuerySuite:
    suite_id: str
    description: str
    queries: tuple[QueryCase, ...]


def _object(value: object, context: str) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"{context} must be a JSON object")
    return cast("Mapping[str, object]", value)


def _non_blank_string(value: object, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{context} must be a non-blank string")
    return value


def load_query_suite(path: Path) -> QuerySuite:
    raw_suite = cast("object", json.loads(path.read_text(encoding="utf-8")))
    suite = _object(raw_suite, "query suite")
    raw_queries = suite.get("queries")
    if not isinstance(raw_queries, list) or not raw_queries:
        raise ValueError("query suite queries must be a non-empty array")

    queries: list[QueryCase] = []
    seen_ids: set[str] = set()
    for index, raw_query in enumerate(cast("list[object]", raw_queries)):
        query = _object(raw_query, f"queries[{index}]")
        query_id = _non_blank_string(query.get("id"), f"queries[{index}].id")
        if query_id in seen_ids:
            raise ValueError(f"duplicate query id: {query_id}")
        seen_ids.add(query_id)
        queries.append(
            QueryCase(
                query_id=query_id,
                text=_non_blank_string(query.get("text"), f"queries[{index}].text"),
                purpose=_non_blank_string(query.get("purpose"), f"queries[{index}].purpose"),
            )
        )

    return QuerySuite(
        suite_id=_non_blank_string(suite.get("suite_id"), "suite_id"),
        description=_non_blank_string(suite.get("description"), "description"),
        queries=tuple(queries),
    )


def build_qdrant_query(
    vector: Sequence[float],
    *,
    document_version_id: UUID,
    top_k: int,
) -> Mapping[str, object]:
    if top_k < 1:
        raise ValueError("top_k must be positive")
    return {
        "query": list(vector),
        "filter": {
            "must": [
                {
                    "key": "document_version_id",
                    "match": {"value": str(document_version_id)},
                }
            ]
        },
        "limit": top_k,
        "with_payload": True,
        "with_vector": False,
    }


def parse_query_results(payload: object) -> list[Mapping[str, object]]:
    response = _object(payload, "Qdrant query response")
    result = _object(response.get("result"), "Qdrant query result")
    raw_points = result.get("points")
    if not isinstance(raw_points, list):
        raise ValueError("Qdrant query result points must be an array")

    results: list[Mapping[str, object]] = []
    for rank, raw_point in enumerate(cast("list[object]", raw_points), start=1):
        point = _object(raw_point, f"Qdrant point at rank {rank}")
        score = point.get("score")
        if isinstance(score, bool) or not isinstance(score, (int, float)):
            raise ValueError(f"Qdrant point at rank {rank} has an invalid score")
        result_record: dict[str, object] = {
            "rank": rank,
            "point_id": _non_blank_string(point.get("id"), f"point at rank {rank}.id"),
            "score": float(score),
            "payload": _object(point.get("payload"), f"point at rank {rank}.payload"),
        }
        results.append(result_record)
    return results


def current_git_revision() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    revision = completed.stdout.strip()
    return revision if completed.returncode == 0 and revision else "unknown"


def _embedding_config(settings: EmbeddingSettings) -> TeiEmbeddingConfig:
    return TeiEmbeddingConfig(
        base_url=settings.base_url,
        model_id=settings.model_id,
        model_revision=settings.model_revision,
        vector_dimension=settings.vector_dimension,
        batch_size=settings.batch_size,
        timeout_seconds=settings.timeout_seconds,
        api_key=(settings.api_key.get_secret_value() if settings.api_key is not None else None),
    )


async def capture_baseline(
    suite: QuerySuite,
    *,
    document_version_id: UUID,
    top_k: int,
    embedding_settings: EmbeddingSettings,
    qdrant_settings: QdrantSettings,
    git_revision: str,
) -> Mapping[str, object]:
    qdrant_headers = (
        {"api-key": qdrant_settings.api_key.get_secret_value()}
        if qdrant_settings.api_key is not None
        else None
    )
    async with (
        TeiEmbeddingProvider(_embedding_config(embedding_settings)) as embedding_provider,
        httpx.AsyncClient(
            timeout=qdrant_settings.timeout_seconds,
            headers=qdrant_headers,
        ) as qdrant_client,
    ):
        embeddings = await embedding_provider.embed([query.text for query in suite.queries])
        collection_response = await qdrant_client.get(
            f"{qdrant_settings.url.rstrip('/')}/collections/{qdrant_settings.collection}"
        )
        collection_response.raise_for_status()
        collection_payload = _object(
            cast("object", collection_response.json()), "Qdrant collection response"
        )

        captured_queries: list[Mapping[str, object]] = []
        for query, vector in zip(suite.queries, embeddings.vectors, strict=True):
            query_response = await qdrant_client.post(
                (
                    f"{qdrant_settings.url.rstrip('/')}/collections/"
                    f"{qdrant_settings.collection}/points/query"
                ),
                json=build_qdrant_query(
                    vector,
                    document_version_id=document_version_id,
                    top_k=top_k,
                ),
            )
            query_response.raise_for_status()
            captured_queries.append(
                {
                    **asdict(query),
                    "results": parse_query_results(cast("object", query_response.json())),
                }
            )

    return {
        "schema_version": 1,
        "captured_at": datetime.now(UTC).isoformat(),
        "git_revision": git_revision,
        "suite": {
            "suite_id": suite.suite_id,
            "description": suite.description,
        },
        "target": {
            "document_version_id": str(document_version_id),
            "qdrant_collection": qdrant_settings.collection,
            "top_k": top_k,
        },
        "embedding_profile": {
            "model_id": embeddings.model.model_id,
            "model_revision": embeddings.model.model_revision,
            "vector_dimension": embeddings.model.vector_dimension,
            "query_instruction": None,
        },
        "qdrant_collection_info": collection_payload.get("result"),
        "queries": captured_queries,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Capture a filtered similarity-search baseline from TEI and Qdrant."
    )
    parser.add_argument("--suite", required=True, type=Path)
    parser.add_argument("--document-version-id", required=True, type=UUID)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--top-k", type=int, default=5)
    return parser.parse_args()


async def async_main() -> None:
    args = parse_args()
    suite = load_query_suite(args.suite)
    baseline = await capture_baseline(
        suite,
        document_version_id=args.document_version_id,
        top_k=args.top_k,
        embedding_settings=EmbeddingSettings(),  # pyright: ignore[reportCallIssue]
        qdrant_settings=QdrantSettings(),  # pyright: ignore[reportCallIssue]
        git_revision=current_git_revision(),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(baseline, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Captured {len(suite.queries)} queries to {args.output}")


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
