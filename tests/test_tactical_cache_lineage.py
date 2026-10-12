"""Source-representation hash tests with invented encoded rows only."""
import importlib.util
from pathlib import Path
import sqlite3
import unittest

spec=importlib.util.spec_from_file_location('cache_check',Path(__file__).parents[1]/'scripts/research/check_tennis_cache_lineage.py')
check=importlib.util.module_from_spec(spec);spec.loader.exec_module(check)

class CacheFidelityTests(unittest.TestCase):
    def database(self,rows):
        db=sqlite3.connect(':memory:')
        db.execute('CREATE TABLE points(corpus TEXT,match_id TEXT,pt INTEGER,payload TEXT,source_file TEXT,source_row INTEGER)')
        db.executemany('INSERT INTO points VALUES(?,?,?,?,?,?)',rows)
        self.addCleanup(db.close);return db
    def test_canonical_row_order_independent_of_insertion(self):
        rows=[('m','invented',2,'opaque-b','source.csv',3),('m','invented',1,'opaque-a','source.csv',2)]
        self.assertEqual(check.digest_rows(self.database(rows)),check.digest_rows(self.database(rows[::-1])))
    def test_payload_and_source_line_changes_are_detected(self):
        rows=[('m','invented',1,'opaque-a','source.csv',2)]
        initial=check.digest_rows(self.database(rows))
        for changed in [('m','invented',1,'opaque-b','source.csv',2),('m','invented',1,'opaque-a','source.csv',3)]:
            self.assertNotEqual(initial,check.digest_rows(self.database([changed])))

if __name__=='__main__':unittest.main()
