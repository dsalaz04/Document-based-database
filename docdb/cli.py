"""Command-line interface: scriptable subcommands plus the interactive menu."""

from __future__ import annotations

import argparse
import sys

from .errors import DocDBError
from .storage import Database


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="docdb",
        description="A fixed-length-record document database.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_import = sub.add_parser("import", help="build a database from a CSV file")
    p_import.add_argument("csv")
    p_import.add_argument("name", help="output database name (no extension)")
    p_import.add_argument("--key", required=True, help="field to index/sort on")

    p_schema = sub.add_parser("schema", help="print a database's layout")
    p_schema.add_argument("name")

    p_get = sub.add_parser("get", help="look up a record by key")
    p_get.add_argument("name")
    p_get.add_argument("key", type=int)

    p_add = sub.add_parser("add", help="add a record (field=value pairs)")
    p_add.add_argument("name")
    p_add.add_argument("pairs", nargs="+", metavar="field=value")

    p_update = sub.add_parser("update", help="update one field of a record")
    p_update.add_argument("name")
    p_update.add_argument("key", type=int)
    p_update.add_argument("field")
    p_update.add_argument("value")

    p_delete = sub.add_parser("delete", help="delete a record by key")
    p_delete.add_argument("name")
    p_delete.add_argument("key", type=int)

    p_report = sub.add_parser("report", help="print the first N records")
    p_report.add_argument("name")
    p_report.add_argument("--limit", type=int, default=10)

    p_compact = sub.add_parser("compact", help="drop deleted slots and rewrite")
    p_compact.add_argument("name")

    p_menu = sub.add_parser("menu", help="run the interactive menu")
    p_menu.add_argument("name", nargs="?", help="optional database to open on start")

    args = parser.parse_args(argv)
    try:
        return _dispatch(args)
    except DocDBError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


def _dispatch(args) -> int:
    if args.command == "import":
        db = Database.import_csv(args.csv, args.name, key=args.key)
        print(f"Imported {db.record_count()} records into {args.name}.data "
              f"(key={args.key}, record_size={db.schema.record_size} bytes)")
        db.close()
        return 0

    if args.command == "menu":
        from .repl import Repl
        db = Database.open(args.name) if args.name else None
        Repl(db).run()
        return 0

    with Database.open(args.name) as db:
        if args.command == "schema":
            print(f"key: {db.schema.key}")
            print(f"record_size: {db.schema.record_size} bytes "
                  f"(+1 newline = {db.schema.line_size})")
            for f in db.schema.fields:
                print(f"  {f.name:<12} width {f.width}")
        elif args.command == "get":
            record = db.get(args.key)
            print(_format(record, db) if record else f"Record {args.key} not found")
        elif args.command == "add":
            db.add(_parse_pairs(args.pairs))
            print("Record added.")
        elif args.command == "update":
            db.update(args.key, args.field, args.value)
            print("Record updated.")
        elif args.command == "delete":
            db.delete(args.key)
            print(f"Record {args.key} deleted.")
        elif args.command == "report":
            for record in db.report(limit=args.limit):
                print(_format(record, db))
        elif args.command == "compact":
            print(f"Compacted; {db.compact()} records remain.")
    return 0


def _parse_pairs(pairs: list[str]) -> dict[str, str]:
    out = {}
    for pair in pairs:
        if "=" not in pair:
            raise DocDBError(f"expected field=value, got {pair!r}")
        field, value = pair.split("=", 1)
        out[field] = value
    return out


def _format(record, db: Database) -> str:
    return "  ".join(f"{n}={v}" for n, v in record.as_dict(db.schema).items())
