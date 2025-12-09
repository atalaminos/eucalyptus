import sqlite3
from typing import Optional

from utils.utils_log import UtilsLog


class Sqlite:
    def __init__(self, filename):
        try:
            self.conn = sqlite3.connect(filename, check_same_thread=False)
            cur = self.conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT NOT NULL UNIQUE,
                    value TEXT NOT NULL
                )
            """)
        except Exception as e:
            UtilsLog.error(f'Sqlite (__init__): {e}')

    def get(self, key: str) -> Optional[str]:
        try:
            cur = self.conn.cursor()
            cur.execute("SELECT value FROM data where key = ?", (key,))
            data = cur.fetchone()
            return data
        except Exception as e:
            UtilsLog.error(f'Sqlite (get): {e}')
            return None

    def set(self, key: str, value: str) -> bool:
        try:
            cur = self.conn.cursor()
            cur.execute("""
                INSERT INTO data (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """, (key, value))
            self.conn.commit()
            return True
        except Exception as e:
            UtilsLog.error(f"Sqlite (set): {e}")
            return False

    def truncate(self) -> bool:
        try:
            cur = self.conn.cursor()
            cur.execute("DELETE FROM data")
            self.conn.commit()
            return True
        except Exception as e:
            UtilsLog.error(f"Sqlite (truncate): {e}")
            return False

    def close(self):
        try:
            self.conn.close()
        except Exception as e:
            UtilsLog.error(f'Sqlite (close): {e}')
            return False
