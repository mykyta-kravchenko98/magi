"""Factory for independent documents transaction boundaries."""

from typing import Protocol

from magi.documents.application.interfaces.unit_of_work import UnitOfWork


class UnitOfWorkFactory(Protocol):
    def __call__(self) -> UnitOfWork: ...
