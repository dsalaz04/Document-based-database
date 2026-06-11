"""Typed exceptions, so callers can distinguish real failures from a closed database."""


class DocDBError(Exception):
    """Base class for all docdb errors."""


class NoDatabaseOpen(DocDBError):
    """An operation needed an open database but none was open."""


class SchemaError(DocDBError):
    """The config/schema is missing, malformed, or inconsistent with a request."""


class RecordNotFound(DocDBError):
    """No live record exists for the requested key."""


class DuplicateKey(DocDBError):
    """A record with the requested key already exists."""


class FieldError(DocDBError):
    """A field value is invalid (e.g. wider than its column, or not a valid key)."""
