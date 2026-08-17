"""Semantic content role stored in the vector projection."""

from typing import Literal

type VectorContentRole = Literal[
    "body",
    "table_of_contents",
    "header_footer",
    "front_matter",
]
