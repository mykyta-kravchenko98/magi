from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

from magi.shared.persistence import NAMING_CONVENTION

RETRIEVAL_SCHEMA = "retrieval"


class RetrievalBase(DeclarativeBase):
    metadata = MetaData(schema=RETRIEVAL_SCHEMA, naming_convention=NAMING_CONVENTION)
