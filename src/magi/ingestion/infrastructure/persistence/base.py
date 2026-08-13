from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

from magi.shared.persistence import NAMING_CONVENTION

INGESTION_SCHEMA = "ingestion"


class IngestionBase(DeclarativeBase):
    metadata = MetaData(schema=INGESTION_SCHEMA, naming_convention=NAMING_CONVENTION)
