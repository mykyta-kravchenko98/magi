"""Application-owned object-storage failures."""


class ObjectStorageError(Exception):
    """An object-storage operation could not be completed."""


class ObjectAlreadyExistsError(ObjectStorageError):
    """An immutable object key is already occupied."""
