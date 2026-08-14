from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

from magi.shared.persistence import NAMING_CONVENTION

DOCUMENTS_SCHEMA = "documents"


class DocumentsBase(DeclarativeBase):
    metadata = MetaData(schema=DOCUMENTS_SCHEMA, naming_convention=NAMING_CONVENTION)
