"""Validated upload values used inside the upload use case."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class ValidatedUpload:
    filename: str
    media_type: str
