from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

from magi.documents.infrastructure.persistence.base import DocumentsBase
from magi.ingestion.infrastructure.persistence.base import IngestionBase
from magi.retrieval.infrastructure.persistence.base import RetrievalBase

EXPECTED_HEADS = {
    "documents": "documents_0001",
    "ingestion": "ingestion_0001",
    "retrieval": "retrieval_0001",
}


def test_contexts_have_separate_metadata_and_schemas() -> None:
    bases = (DocumentsBase, IngestionBase, RetrievalBase)

    assert [base.metadata.schema for base in bases] == ["documents", "ingestion", "retrieval"]
    assert len({id(base.metadata) for base in bases}) == len(bases)


def test_contexts_have_independent_migration_heads() -> None:
    config_path = Path(__file__).parents[1] / "alembic.ini"

    heads = {
        context_name: ScriptDirectory.from_config(
            Config(config_path, ini_section=context_name)
        ).get_current_head()
        for context_name in EXPECTED_HEADS
    }

    assert heads == EXPECTED_HEADS
