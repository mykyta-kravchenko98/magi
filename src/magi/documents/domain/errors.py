"""Errors raised when a documents domain rule is violated."""


class DomainRuleViolation(ValueError):
    """A documents aggregate invariant was violated."""


class InvalidStateTransition(DomainRuleViolation):
    """An aggregate cannot perform an operation from its current state."""
