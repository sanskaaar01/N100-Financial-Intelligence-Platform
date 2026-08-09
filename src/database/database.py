from pathlib import Path
import sqlite3


class Database:
    def __init__(self, db_name="nifty100.db"):
        root = Path(__file__).resolve().parents[2]
        db_dir = root / "db"
        db_dir.mkdir(exist_ok=True)

        self.db_path = db_dir / db_name

    def connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn