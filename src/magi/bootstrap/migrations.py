from pathlib import Path

from alembic import command
from alembic.config import Config

MIGRATION_CONTEXTS = ("documents", "ingestion", "retrieval")


def upgrade_all(config_path: Path = Path("alembic.ini")) -> None:
    for context_name in MIGRATION_CONTEXTS:
        config = Config(config_path, ini_section=context_name)
        command.upgrade(config, "head")


def main() -> None:
    upgrade_all()
