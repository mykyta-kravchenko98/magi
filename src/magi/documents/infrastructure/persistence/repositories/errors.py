"""Errors raised by documents repository adapters."""


class AggregateNotFoundError(LookupError):
    """An aggregate selected for persistence no longer exists."""
