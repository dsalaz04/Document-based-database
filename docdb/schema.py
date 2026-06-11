"""On-disk schema: the fixed-width record layout, plus encode/decode helpers.

A database is two files that share a base name:

  <name>.config   a JSON description of the record layout (this module)
  <name>.data     fixed-length records, one per line, padded to `record_size` bytes

Because every record occupies exactly the same number of bytes, record N lives at a
known byte offset, which is what makes O(1) seeks and binary search possible.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .errors import FieldError, SchemaError

NEWLINE = b"\n"
SEPARATOR = b" "  # one space between columns, for human readability


@dataclass(frozen=True)
class Field:
    name: str
    width: int  # column width in bytes


@dataclass(frozen=True)
class Schema:
    fields: tuple[Field, ...]
    key: str  # name of the (integer) key field records are sorted by

    # --- derived geometry -------------------------------------------------

    @property
    def key_index(self) -> int:
        for i, f in enumerate(self.fields):
            if f.name == self.key:
                return i
        raise SchemaError(f"key field {self.key!r} is not one of {self.names()}")

    @property
    def record_size(self) -> int:
        """Bytes in one record: every column, plus a separator between each pair."""
        return sum(f.width for f in self.fields) + len(SEPARATOR) * (len(self.fields) - 1)

    @property
    def line_size(self) -> int:
        """Bytes consumed on disk by one record, including its trailing newline."""
        return self.record_size + len(NEWLINE)

    def names(self) -> list[str]:
        return [f.name for f in self.fields]

    def width_of(self, name: str) -> int:
        for f in self.fields:
            if f.name == name:
                return f.width
        raise FieldError(f"no such field {name!r}; fields are {self.names()}")

    # --- (de)serialization of a single record -----------------------------

    def encode(self, values: list[str]) -> bytes:
        """Pack field values into a fixed-width record (no newline)."""
        if len(values) != len(self.fields):
            raise FieldError(f"expected {len(self.fields)} fields, got {len(values)}")
        chunks = []
        for value, field in zip(values, self.fields):
            raw = str(value).encode("utf-8")
            if len(raw) > field.width:
                raise FieldError(
                    f"value {value!r} is {len(raw)} bytes, wider than "
                    f"column {field.name!r} ({field.width})"
                )
            chunks.append(raw.ljust(field.width))  # left-justify, pad with spaces
        return SEPARATOR.join(chunks)

    def decode(self, raw: bytes) -> list[str] | None:
        """Unpack a record into field values, or None if the slot is a tombstone."""
        if raw.strip() == b"":  # a blank record marks a deleted slot
            return None
        values = []
        pos = 0
        for field in self.fields:
            chunk = raw[pos : pos + field.width]
            pos += field.width + len(SEPARATOR)
            values.append(chunk.decode("utf-8").rstrip(" "))
        return values

    def tombstone(self) -> bytes:
        return b" " * self.record_size

    # --- config file I/O --------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "fields": [{"name": f.name, "width": f.width} for f in self.fields],
        }

    @classmethod
    def from_dict(cls, data: dict) -> Schema:
        try:
            fields = tuple(Field(f["name"], int(f["width"])) for f in data["fields"])
            schema = cls(fields=fields, key=data["key"])
        except (KeyError, TypeError, ValueError) as e:
            raise SchemaError(f"malformed config: {e}") from e
        schema.key_index  # validate the key references a real field
        return schema

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> Schema:
        if not path.is_file():
            raise SchemaError(f"config file not found: {path}")
        return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))
