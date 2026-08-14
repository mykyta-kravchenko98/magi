"""Media-type parser registry."""

from collections.abc import Mapping

from magi.ingestion.application.interfaces import DocumentFormatParser
from magi.ingestion.domain import ParsedDocument, UnsupportedMediaTypeError


class DocumentParserRegistry:
    """Select a parser by media type; extra adapters are supplied by composition."""

    def __init__(
        self,
        *,
        parsers: Mapping[str, DocumentFormatParser],
    ) -> None:
        if not parsers:
            raise ValueError("at least one document parser must be configured")
        normalized_parsers: dict[str, DocumentFormatParser] = {}
        for media_type, parser in parsers.items():
            normalized_media_type = media_type.strip().lower()
            if ";" in normalized_media_type or "/" not in normalized_media_type:
                raise ValueError(f"invalid parser media type: {media_type}")
            if normalized_media_type in normalized_parsers:
                raise ValueError(f"parser already registered: {normalized_media_type}")
            normalized_parsers[normalized_media_type] = parser
        self._parsers = normalized_parsers

    def parse(self, content: bytes, media_type: str) -> ParsedDocument:
        base_type, *parameters = (part.strip().lower() for part in media_type.split(";"))
        for parameter in parameters:
            is_utf8_text = base_type.startswith("text/") and parameter in {
                "charset=utf-8",
                'charset="utf-8"',
            }
            if not is_utf8_text:
                raise UnsupportedMediaTypeError(f"unsupported media type parameter: {parameter}")
        parser = self._parsers.get(base_type)
        if parser is None:
            raise UnsupportedMediaTypeError(f"unsupported media type: {base_type}")
        return parser.parse(content)
