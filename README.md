# Document-based Database

A small **document database backed by fixed-length records on disk**, written in pure
Python (no dependencies). It imports a CSV into a compact, self-describing on-disk format
and supports the full set of CRUD operations — with **binary search** straight to a
record by key, because every record is the same size and lives at a known byte offset.

It began as a class assignment hard-wired to one dataset; this is the schema-generic,
tested, scriptable version of the same idea.

## The on-disk format

Each database is two files that share a base name:

```
parks.config   JSON describing the record layout (field names + column widths + key)
parks.data     fixed-width records, one per line, each padded to record_size bytes
```

Example `.config`:

```json
{
  "key": "ID",
  "fields": [
    { "name": "ID", "width": 2 },
    { "name": "Name", "width": 35 },
    { "name": "Visitors", "width": 8 }
  ]
}
```

A record is each field left-justified and space-padded to its column width, joined by a
single space, then a newline. Records are kept **sorted by the integer key**, so a lookup
binary-searches the file: seek to the middle record, compare keys, halve the range. A
**delete** blanks a record in place (a "tombstone", O(1)); the binary search skips
tombstones, and `add`/`compact` rewrite the file dense and sorted.

## Quick start

Requires Python 3.10+. No installation, no dependencies.

```bash
make demo     # import the sample CSV and print the schema + a report
make test     # run the unit tests
make menu     # import the sample data and open the interactive menu
```

## Usage

Build a database from any CSV (its header row names the fields; pick one integer column
as the key):

```bash
python3 -m docdb import sample/parks.csv parks --key ID
```

Then query and mutate it:

```bash
python3 -m docdb schema parks
python3 -m docdb get    parks 57
python3 -m docdb add    parks ID=50 Region=PW State=CA Code=PINN "Name=Pinnacles National Park" "Type=National Park" Visitors=275023
python3 -m docdb update parks 15 Visitors 5000000
python3 -m docdb delete parks 22
python3 -m docdb report parks --limit 5
python3 -m docdb compact parks
```

Or use the original-style interactive menu:

```bash
python3 -m docdb menu parks
```

### Commands

| Command   | Description |
| --------- | ----------- |
| `import`  | Build a `.config` + `.data` pair from a CSV (`--key FIELD`) |
| `schema`  | Print the record layout and sizes |
| `get`     | Binary-search for a record by key |
| `add`     | Insert a record from `field=value` pairs (kept sorted) |
| `update`  | Change one field of an existing record (in place) |
| `delete`  | Tombstone a record |
| `report`  | Print the first N records (`--limit`) |
| `compact` | Drop tombstones and rewrite the file |
| `menu`    | Interactive 1–9 menu |

## What changed from the original

The original `Database.py` was a single 500-line menu app. The behavior is preserved, but:

- **Schema-generic.** The original hard-coded the national-parks fields and column widths
  (`2,2,4,83,37,9`) in its add/update paths, so it only worked for one CSV. Layout is now
  derived entirely from the config, so it works for any CSV.
- **Correct fixed-width padding.** The original padded with `ljust(width - len(value))`,
  which (since `ljust` takes a *total* width) effectively did nothing — records weren't
  reliably padded to a fixed size, undermining the seek/binary-search premise. Fixed.
- **Real error handling.** Bare `except:` blocks that reported every failure as "please
  open the database first" are replaced with typed exceptions (`RecordNotFound`,
  `DuplicateKey`, `FieldError`, ...).
- **Robust I/O.** Files are opened via context managers in binary mode with explicit
  newlines, instead of leaking a fresh handle on every read and relying on a per-OS
  newline-size fudge factor.
- **Scriptable + testable.** A real `argparse` CLI sits alongside the interactive menu,
  and a stdlib `unittest` suite covers import, CRUD, binary search across tombstones, and
  compaction.

## Project structure

```
docdb/
  schema.py     # fixed-width record layout + encode/decode + config I/O
  storage.py    # the engine: import, seek/read, binary search, CRUD, compaction
  repl.py       # interactive 1-9 menu (schema-generic)
  cli.py        # argparse command-line interface
  errors.py     # typed exceptions
  __main__.py   # `python -m docdb`
sample/parks.csv
tests/test_docdb.py
Makefile
```

## License

MIT.
