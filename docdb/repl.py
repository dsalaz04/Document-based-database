"""The interactive menu — the original program's 1-9 loop, now schema-generic.

Prompts are generated from the open database's schema, so the menu works for any CSV,
not just the national-parks dataset the original hard-coded.
"""

from __future__ import annotations

from .errors import DocDBError
from .storage import Database

MENU = """
  1. Open database
  2. Close database
  3. Display record
  4. Update record
  5. Create report
  6. Add record
  7. Delete record
  8. Compact (drop deleted slots)
  9. Quit
"""


class Repl:
    def __init__(self, db: Database | None = None):
        self.db = db

    def run(self) -> None:
        while True:
            print(MENU)
            choice = input("Select an option (1-9): ").strip()
            try:
                if choice == "1":
                    self._open()
                elif choice == "2":
                    self._close()
                elif choice == "3":
                    self._display()
                elif choice == "4":
                    self._update()
                elif choice == "5":
                    self._report()
                elif choice == "6":
                    self._add()
                elif choice == "7":
                    self._delete()
                elif choice == "8":
                    self._compact()
                elif choice == "9":
                    self._close()
                    print("\nQuitting...")
                    return
                elif choice:
                    print("Not a valid choice.")
            except DocDBError as e:
                print(f"error: {e}")
            except (EOFError, KeyboardInterrupt):
                print("\nQuitting...")
                self._close()
                return

    # --- menu actions -----------------------------------------------------

    def _require_db(self) -> Database:
        if self.db is None:
            raise DocDBError("no database open — choose option 1 first")
        return self.db

    def _open(self) -> None:
        if self.db is not None:
            print("A database is already open. Close it first.")
            return
        name = input("Database name (no extension): ").strip()
        self.db = Database.open(name)
        print(f"Opened {name} ({self.db.record_count()} slots).")

    def _close(self) -> None:
        if self.db is not None:
            self.db.close()
            self.db = None
            print("Database closed.")

    def _display(self) -> None:
        db = self._require_db()
        key = int(input("Record ID to display: "))
        record = db.get(key)
        print(_format(record, db) if record else f"Record {key} not found")

    def _update(self) -> None:
        db = self._require_db()
        key = int(input("Record ID to update: "))
        record = db.get(key)
        if record is None:
            print(f"Record {key} not found")
            return
        print(_format(record, db))
        editable = [n for n in db.schema.names() if n != db.schema.key]
        for i, name in enumerate(editable, 1):
            print(f"  {i}) {name}")
        sel = input("Field number to update (blank to cancel): ").strip()
        if not sel:
            return
        field = editable[int(sel) - 1]
        value = input(f"New value for {field}: ")
        db.update(key, field, value)
        print("Record updated.")

    def _report(self) -> None:
        db = self._require_db()
        for record in db.report(limit=10):
            print(_format(record, db))

    def _add(self) -> None:
        db = self._require_db()
        values = {}
        for field in db.schema.fields:
            values[field.name] = input(f"{field.name} (<= {field.width} chars): ")
        db.add(values)
        print("Record added.")

    def _delete(self) -> None:
        db = self._require_db()
        key = int(input("Record ID to delete: "))
        db.delete(key)
        print(f"Record {key} deleted.")

    def _compact(self) -> None:
        db = self._require_db()
        remaining = db.compact()
        print(f"Compacted; {remaining} records remain.")


def _format(record, db: Database) -> str:
    return "  ".join(f"{n}={v}" for n, v in record.as_dict(db.schema).items())
