"""Общее подключение и выполнение именованных SQL-запросов ПР7."""

import re
import sqlite3
from functools import lru_cache
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "reminderly.sqlite"
QUERIES_FILE = BASE_DIR / "sql" / "queries.sql"


def get_connection(db_path=None):
    """Создать соединение с включёнными FK и доступом к полям по имени."""
    conn = sqlite3.connect(db_path if db_path is not None else DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@lru_cache(maxsize=1)
def load_queries():
    """Прочитать запросы по меткам -- name: ... из sql/queries.sql."""
    source = QUERIES_FILE.read_text(encoding="utf-8")
    chunks = re.split(r"(?m)^-- name: ([a-z_]+)\s*$", source)
    queries = {}
    for index in range(1, len(chunks), 2):
        name = chunks[index]
        query = chunks[index + 1].split(";", 1)[0].strip()
        if not query or name in queries:
            raise ValueError(f"Некорректный SQL-запрос: {name}")
        queries[name] = query
    return queries


def fetch_all(name, params=()):
    """Выполнить SELECT с параметрами и вернуть список sqlite3.Row."""
    query = load_queries()[name]
    conn = get_connection()
    try:
        return conn.execute(query, params).fetchall()
    finally:
        conn.close()


def fetch_one(name, params=()):
    """Выполнить SELECT, вернуть строку или None."""
    query = load_queries()[name]
    conn = get_connection()
    try:
        return conn.execute(query, params).fetchone()
    finally:
        conn.close()


def fetch_record(table, object_id):
    """Получить одну запись по ID из предопределённого списка таблиц."""
    if table not in {"users", "categories", "times"}:
        raise ValueError("Неизвестная таблица")
    conn = get_connection()
    try:
        return conn.execute(
            f"SELECT * FROM {table} WHERE id = ?", (object_id,)
        ).fetchone()
    finally:
        conn.close()
