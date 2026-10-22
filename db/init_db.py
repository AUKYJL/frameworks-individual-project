"""Создание таблиц SQLite из sql/schema.sql: python -m db.init_db."""

from db.database import BASE_DIR, get_connection


def init_database(db_path=None):
    """Применить схему без удаления уже существующих записей."""
    (BASE_DIR / "data").mkdir(exist_ok=True)
    conn = get_connection(db_path)
    try:
        conn.executescript(
            (BASE_DIR / "sql" / "schema.sql").read_text(encoding="utf-8")
        )
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    init_database()
    print("Таблицы SQLite готовы.")
