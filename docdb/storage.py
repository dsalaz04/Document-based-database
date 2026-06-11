"""The fixed-length-record storage engine.

Records are kept sorted by their integer key, so a key lookup is a binary search that
seeks straight to the middle record without scanning. Deletes leave a blank "tombstone"
in place (O(1)); `add` and `compact` rewrite the file dense and sorted, dropping any
tombstones.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from .errors import DuplicateKey, FieldError, NoDatabaseOpen, RecordNotFound
from .schema import NEWLINE, Field, Schema


@dataclass
class Record:
    index: int            # physical slot in the data file
    values: list[str]     # field values, in schema order

    def as_dict(self, schema: Schema) -> dict[str, str]:
        return dict(zip(schema.names(), self.values))


class Database:
    """A single open document database (a `.config` + `.data` pair)."""

    def __init__(self, base: Path, schema: Schema):
        self.base = base
        self.schema = schema
        self.data_path = base.with_suffix(".data")
        self.config_path = base.with_suffix(".config")
        self._file = open(self.data_path, "r+b")

    # --- lifecycle --------------------------------------------------------

    @classmethod
    def open(cls, name: str | Path) -> "Database":
        base = Path(name)
        schema = Schema.load(base.with_suffix(".config"))
        if not base.with_suffix(".data").is_file():
            raise NoDatabaseOpen(f"data file not found: {base.with_suffix('.data')}")
        return cls(base, schema)

    @classmethod
    def import_csv(cls, csv_path: str | Path, name: str | Path, key: str) -> "Database":
        """Build a new database from a CSV file (its header row names the fields)."""
        csv_path = Path(csv_path)
        with open(csv_path, newline="", encoding="utf-8") as fh:
            reader = csv.reader(fh)
            header = next(reader)
            rows = [row for row in reader if any(cell.strip() for cell in row)]

        if key not in header:
            raise FieldError(f"key field {key!r} not in CSV header {header}")
        key_index = header.index(key)

        # Column width = widest value seen (at least 1), measured in bytes. Field names
        # aren't stored in the data file, so they don't constrain the width.
        widths = [1] * len(header)
        for row in rows:
            for i, cell in enumerate(row):
                widths[i] = max(widths[i], len(cell.encode("utf-8")))

        # Keys must be integers (we sort and binary-search on them) and unique.
        seen: set[int] = set()
        for row in rows:
            k = _as_int(row[key_index], key)
            if k in seen:
                raise DuplicateKey(f"duplicate key {k} in {csv_path}")
            seen.add(k)
        rows.sort(key=lambda r: int(r[key_index]))

        schema = Schema(tuple(Field(n, w) for n, w in zip(header, widths)), key)
        base = Path(name)
        schema.save(base.with_suffix(".config"))
        with open(base.with_suffix(".data"), "wb") as out:
            for row in rows:
                out.write(schema.encode(row) + NEWLINE)
        return cls(base, schema)

    def close(self) -> None:
        if not self._file.closed:
            self._file.close()

    def __enter__(self) -> "Database":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # --- low-level record access -----------------------------------------

    def record_count(self) -> int:
        """Number of physical slots (live records plus tombstones)."""
        self._require_open()
        return self.data_path.stat().st_size // self.schema.line_size

    def _read(self, index: int) -> list[str] | None:
        self._file.seek(index * self.schema.line_size)
        raw = self._file.read(self.schema.record_size)
        return self.schema.decode(raw)

    def _write(self, index: int, raw: bytes) -> None:
        self._file.seek(index * self.schema.line_size)
        self._file.write(raw + NEWLINE)
        self._file.flush()

    def _require_open(self) -> None:
        if self._file.closed:
            raise NoDatabaseOpen("the database is closed")

    # --- queries ----------------------------------------------------------

    def get(self, key: int) -> Record | None:
        """Binary search for a key, transparently skipping tombstones."""
        self._require_open()
        lo, hi = 0, self.record_count() - 1
        while lo <= hi:
            mid = (lo + hi) // 2
            values = self._read(mid)
            if values is None:
                # Landed on a tombstone: probe right for the nearest live record.
                probe = mid + 1
                while probe <= hi and self._read(probe) is None:
                    probe += 1
                if probe > hi:
                    hi = mid - 1  # right half is all tombstones; search left
                    continue
                mid, values = probe, self._read(probe)
            found = int(values[self.schema.key_index])
            if found == key:
                return Record(mid, values)
            if found < key:
                lo = mid + 1
            else:
                hi = mid - 1
        return None

    def scan(self) -> Iterator[Record]:
        """Yield live records in key order (skips tombstones)."""
        self._require_open()
        for index in range(self.record_count()):
            values = self._read(index)
            if values is not None:
                yield Record(index, values)

    def report(self, limit: int = 10) -> list[Record]:
        out = []
        for record in self.scan():
            out.append(record)
            if len(out) >= limit:
                break
        return out

    # --- mutations --------------------------------------------------------

    def update(self, key: int, field: str, value: str) -> Record:
        record = self.get(key)
        if record is None:
            raise RecordNotFound(f"record {key} not found")
        if field not in self.schema.names():
            raise FieldError(f"no such field {field!r}; fields are {self.schema.names()}")
        if field == self.schema.key:
            raise FieldError("the key field cannot be updated; delete and re-add instead")
        record.values[self.schema.names().index(field)] = value
        self._write(record.index, self.schema.encode(record.values))  # validates width
        return record

    def add(self, values: dict[str, str] | list[str]) -> Record:
        """Insert a record, keeping the file sorted (and compacting tombstones)."""
        row = self._normalize(values)
        key = _as_int(row[self.schema.key_index], self.schema.key)
        if self.get(key) is not None:
            raise DuplicateKey(f"record {key} already exists")
        self.schema.encode(row)  # validate widths before touching the file

        rows = [r.values for r in self.scan()]
        rows.append(row)
        rows.sort(key=lambda r: int(r[self.schema.key_index]))
        self._rewrite(rows)
        return self.get(key)  # type: ignore[return-value]

    def delete(self, key: int) -> None:
        record = self.get(key)
        if record is None:
            raise RecordNotFound(f"record {key} not found")
        self._write(record.index, self.schema.tombstone())

    def compact(self) -> int:
        """Drop tombstones and rewrite the file dense. Returns records remaining."""
        rows = [r.values for r in self.scan()]
        self._rewrite(rows)
        return len(rows)

    # --- helpers ----------------------------------------------------------

    def _rewrite(self, rows: list[list[str]]) -> None:
        self._require_open()
        self._file.seek(0)
        self._file.truncate()
        for row in rows:
            self._file.write(self.schema.encode(row) + NEWLINE)
        self._file.flush()

    def _normalize(self, values: dict[str, str] | list[str]) -> list[str]:
        if isinstance(values, dict):
            unknown = set(values) - set(self.schema.names())
            if unknown:
                raise FieldError(f"unknown field(s): {sorted(unknown)}")
            return [str(values.get(name, "")) for name in self.schema.names()]
        if len(values) != len(self.schema.fields):
            raise FieldError(f"expected {len(self.schema.fields)} values, got {len(values)}")
        return [str(v) for v in values]


def _as_int(value: str, field: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        raise FieldError(f"key field {field!r} must be an integer, got {value!r}") from None
