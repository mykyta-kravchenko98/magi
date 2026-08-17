"""Semantic role assigned to extracted document content."""

from enum import StrEnum


class ContentRole(StrEnum):
    BODY = "body"
    TABLE_OF_CONTENTS = "table_of_contents"
    HEADER_FOOTER = "header_footer"
    FRONT_MATTER = "front_matter"
