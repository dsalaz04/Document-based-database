"""Stdlib unittest suite for the docdb engine. Run: python -m unittest discover."""

import tempfile
import unittest
from pathlib import Path

from docdb import Database, DuplicateKey, FieldError, RecordNotFound, Schema
from docdb.schema import Field

SAMPLE = Path(__file__).resolve().parent.parent / "sample" / "parks.csv"
KEYS = [4, 15, 22, 31, 48, 57, 63, 79, 88, 96]


class DocDBTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name) / "parks"
        self.db = Database.import_csv(SAMPLE, self.base, key="ID")

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    # --- import / schema --------------------------------------------------

    def test_import_counts_and_records(self):
        self.assertEqual(self.db.record_count(), len(KEYS))
        self.assertEqual([int(r.values[0]) for r in self.db.scan()], sorted(KEYS))

    def test_record_size_matches_layout(self):
        s = self.db.schema
        self.assertEqual(s.record_size, sum(f.width for f in s.fields) + (len(s.fields) - 1))

    def test_config_roundtrip(self):
        reloaded = Schema.load(self.base.with_suffix(".config"))
        self.assertEqual(reloaded, self.db.schema)

    # --- queries ----------------------------------------------------------

    def test_get_every_key(self):
        for k in KEYS:
            rec = self.db.get(k)
            self.assertIsNotNone(rec)
            self.assertEqual(int(rec.values[0]), k)

    def test_get_missing(self):
        self.assertIsNone(self.db.get(999))

    def test_get_preserves_field_values(self):
        rec = self.db.get(4)
        self.assertEqual(rec.as_dict(self.db.schema)["Name"], "Yosemite National Park")

    # --- update -----------------------------------------------------------

    def test_update_persists_after_reopen(self):
        self.db.update(15, "Visitors", "5000000")
        self.db.close()
        self.db = Database.open(self.base)
        self.assertEqual(self.db.get(15).as_dict(self.db.schema)["Visitors"], "5000000")

    def test_update_too_wide_rejected(self):
        with self.assertRaises(FieldError):
            self.db.update(15, "Code", "WAYTOOLONG")

    def test_update_key_field_rejected(self):
        with self.assertRaises(FieldError):
            self.db.update(15, "ID", "1")

    def test_update_missing_record(self):
        with self.assertRaises(RecordNotFound):
            self.db.update(999, "Code", "X")

    # --- add --------------------------------------------------------------

    def test_add_keeps_sorted_and_findable(self):
        self.db.add({"ID": "50", "Region": "PW", "State": "CA", "Code": "PINN",
                     "Name": "Pinnacles National Park", "Type": "National Park",
                     "Visitors": "275023"})
        self.assertIsNotNone(self.db.get(50))
        keys = [int(r.values[0]) for r in self.db.scan()]
        self.assertEqual(keys, sorted(keys))
        self.assertIn(50, keys)

    def test_add_duplicate_rejected(self):
        with self.assertRaises(DuplicateKey):
            self.db.add({"ID": "4", "Region": "PW", "State": "CA", "Code": "DUPE",
                         "Name": "x", "Type": "y", "Visitors": "1"})

    # --- delete / binary search over tombstones ---------------------------

    def test_delete_then_others_still_found(self):
        for k in (22, 57, 88, 4, 96):  # leave scattered tombstones
            self.db.delete(k)
            self.assertIsNone(self.db.get(k))
        for k in (15, 31, 48, 63, 79):
            self.assertIsNotNone(self.db.get(k), f"binary search lost {k} after deletes")

    def test_delete_missing(self):
        with self.assertRaises(RecordNotFound):
            self.db.delete(999)

    def test_compact_drops_tombstones_preserving_order(self):
        self.db.delete(22)
        self.db.delete(57)
        remaining = self.db.compact()
        self.assertEqual(remaining, len(KEYS) - 2)
        self.assertEqual(self.db.record_count(), len(KEYS) - 2)
        keys = [int(r.values[0]) for r in self.db.scan()]
        self.assertEqual(keys, sorted(keys))
        self.assertNotIn(22, keys)

    def test_add_after_deletes_reuses_space(self):
        self.db.delete(22)
        self.db.delete(57)
        self.db.add({"ID": "5", "Region": "PW", "State": "CA", "Code": "CHIS",
                     "Name": "Channel Islands", "Type": "National Park", "Visitors": "409630"})
        # add() compacts, so the two tombstones are gone and 5 is present and sorted.
        self.assertEqual(self.db.record_count(), len(KEYS) - 2 + 1)
        self.assertIsNotNone(self.db.get(5))


class SchemaUnitTest(unittest.TestCase):
    def setUp(self):
        self.schema = Schema((Field("ID", 3), Field("Name", 5)), key="ID")

    def test_encode_decode_roundtrip(self):
        raw = self.schema.encode(["7", "Bob"])
        self.assertEqual(len(raw), self.schema.record_size)
        self.assertEqual(self.schema.decode(raw), ["7", "Bob"])

    def test_tombstone_decodes_to_none(self):
        self.assertIsNone(self.schema.decode(self.schema.tombstone()))

    def test_encode_rejects_overlong_value(self):
        with self.assertRaises(FieldError):
            self.schema.encode(["7", "Robert"])  # 6 bytes, column width is 5


if __name__ == "__main__":
    unittest.main()
