"""Small validation helpers shared by documents aggregates."""

from magi.documents.domain.errors import DomainRuleViolation


def require_text(value: str, field_name: str) -> None:
    if not value.strip():
        raise DomainRuleViolation(f"{field_name} must not be blank")
