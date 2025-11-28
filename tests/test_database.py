"""
Test database connectivity and basic operations
"""
import unittest
import os
import sqlite3
import sys
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestDatabase(unittest.TestCase):
    """Test database operations"""

    def setUp(self):
        """Set up test database"""
        self.test_db = 'test_upbit_sync.db'

    def tearDown(self):
        """Clean up test database"""
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

    def test_sqlite_connectivity(self):
        """Test basic SQLite connectivity"""
        try:
            conn = sqlite3.connect(self.test_db)
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE test (id INTEGER PRIMARY KEY)")
            cursor.execute("INSERT INTO test (id) VALUES (1)")
            conn.commit()

            cursor.execute("SELECT * FROM test")
            result = cursor.fetchone()
            self.assertEqual(result[0], 1)

            conn.close()
        except Exception as e:
            self.fail(f"Database connectivity test failed: {e}")

    def test_production_database_exists(self):
        """Test that production database exists"""
        db_path = os.path.join(os.path.dirname(
            __file__), '..', 'upbit_sync.db')
        if os.path.exists(db_path):
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                self.assertGreater(
                    len(tables), 0, "Database should have tables")
                conn.close()
            except Exception as e:
                self.fail(f"Production database test failed: {e}")
        else:
            self.skipTest(
                "Production database not found - this is OK for testing environment")


if __name__ == '__main__':
    unittest.main()
