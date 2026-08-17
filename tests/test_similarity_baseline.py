import json
from pathlib import Path
from uuid import UUID

import pytest
from scripts.capture_similarity_baseline import (
    build_qdrant_query,
    load_query_suite,
    parse_query_results,
)

DOCUMENT_VERSION_ID = UUID("bbf15cac-8a40-4831-bc81-732bd958ff24")


def test_checked_in_query_suite_is_valid() -> None:
    suite = load_query_suite(Path("evaluation/pdf-normalization/queries.json"))

    assert suite.suite_id == "ddd-book-pages-1-41-pdf-v1"
    assert len(suite.queries) == 8
    assert len({query.query_id for query in suite.queries}) == len(suite.queries)


def test_checked_in_baseline_is_complete_and_version_filtered() -> None:
    baseline = json.loads(
        Path("evaluation/pdf-normalization/baseline-before-normalization.json").read_text(
            encoding="utf-8"
        )
    )

    assert baseline["schema_version"] == 1
    assert baseline["suite"]["suite_id"] == "ddd-book-pages-1-20-pdf-v1"
    assert baseline["target"]["top_k"] == 5
    assert baseline["embedding_profile"] == {
        "model_id": "Qwen/Qwen3-Embedding-0.6B",
        "model_revision": "97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3",
        "vector_dimension": 1024,
        "query_instruction": None,
    }
    assert len(baseline["queries"]) == 8

    document_version_id = baseline["target"]["document_version_id"]
    for query in baseline["queries"]:
        assert [result["rank"] for result in query["results"]] == [1, 2, 3, 4, 5]
        assert all(
            result["payload"]["document_version_id"] == document_version_id
            for result in query["results"]
        )
        assert all("vector" not in result for result in query["results"])


def test_query_request_is_filtered_to_one_document_version() -> None:
    request = build_qdrant_query(
        (0.1, 0.2, 0.3),
        document_version_id=DOCUMENT_VERSION_ID,
        top_k=5,
    )

    assert request == {
        "query": [0.1, 0.2, 0.3],
        "filter": {
            "must": [
                {
                    "key": "document_version_id",
                    "match": {"value": str(DOCUMENT_VERSION_ID)},
                }
            ]
        },
        "limit": 5,
        "with_payload": True,
        "with_vector": False,
    }


def test_query_results_preserve_rank_score_and_payload() -> None:
    parsed = parse_query_results(
        {
            "result": {
                "points": [
                    {
                        "id": "point-1",
                        "score": 0.75,
                        "payload": {"chunk_index": 3, "text": "A useful chunk"},
                    }
                ]
            },
            "status": "ok",
        }
    )

    assert parsed == [
        {
            "rank": 1,
            "point_id": "point-1",
            "score": 0.75,
            "payload": {"chunk_index": 3, "text": "A useful chunk"},
        }
    ]


def test_query_suite_rejects_duplicate_ids(tmp_path: Path) -> None:
    suite_path = tmp_path / "queries.json"
    suite_path.write_text(
        json.dumps(
            {
                "suite_id": "duplicate-suite",
                "description": "Invalid duplicate example",
                "queries": [
                    {"id": "same", "text": "first", "purpose": "first"},
                    {"id": "same", "text": "second", "purpose": "second"},
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate query id"):
        load_query_suite(suite_path)


@pytest.mark.parametrize("top_k", [0, -1])
def test_query_request_rejects_non_positive_top_k(top_k: int) -> None:
    with pytest.raises(ValueError, match="top_k must be positive"):
        build_qdrant_query(
            (0.1,),
            document_version_id=DOCUMENT_VERSION_ID,
            top_k=top_k,
        )
