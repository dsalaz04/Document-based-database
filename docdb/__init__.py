"""A small document-style database backed by fixed-length records on disk."""

from .errors import (
    DocDBError,
    DuplicateKey,
    FieldError,
    NoDatabaseOpen,
    RecordNotFound,
    SchemaError,
)
from .schema import Field, Schema
from .storage import Database, Record

__all__ = [
    "Database",
    "Record",
    "Schema",
    "Field",
    "DocDBError",
    "NoDatabaseOpen",
    "SchemaError",
    "RecordNotFound",
    "DuplicateKey",
    "FieldError",
]
