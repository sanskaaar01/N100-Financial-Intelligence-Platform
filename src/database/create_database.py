from pathlib import Path

from .database import Database


def create_database():
    db = Database()
    conn = db.connect()

    root = Path(__file__).resolve().parents[2]
    schema = root / "db" / "schema.sql"

    with open(schema, "r", encoding="utf-8") as f:
        conn.executescript(f.read())

    conn.commit()
    conn.close()

    print("SQLite database created successfully.")


if __name__ == "__main__":
    create_database()