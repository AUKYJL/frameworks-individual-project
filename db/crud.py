"""SQLite CRUD для ПР7: операции с пятью таблицами без Django ORM.

Имена таблиц и полей берутся только из конфигурации, значения всегда идут
через параметры sqlite3. Каждое изменение выполняется в транзакции.
"""

from db.database import get_connection
import sqlite3

# Допустимые столбцы задаются разработчиком; из HTTP-запроса имена не берутся.
FIELDS = {
    "users": ("name", "email"),
    "categories": ("name", "description"),
    "times": ("label", "moment"),
    "tasks": (
        "title", "description", "user_id", "category_id", "is_completed"
    ),
    "reminders": (
        "text", "category_id", "remind_at", "user_id", "task_id", "time_id"
    ),
}


class RelatedRecordsError(Exception):
    """Родительскую запись нельзя удалить, пока на неё ссылаются другие."""


def _columns(table):
    try:
        return FIELDS[table]
    except KeyError as error:
        raise ValueError("Неизвестная сущность") from error


def get_item(table, item_id):
    """Получить существующую запись по ID (или None)."""
    _columns(table)
    conn = get_connection()
    try:
        return conn.execute(
            f"SELECT * FROM {table} WHERE id = ?", (item_id,)
        ).fetchone()
    finally:
        conn.close()


def insert_item(table, data):
    """Добавить запись, вернуть созданный ID."""
    columns = _columns(table)
    values = [data[column] for column in columns]
    placeholders = ", ".join("?" for _ in columns)
    conn = get_connection()
    try:
        with conn:
            cursor = conn.execute(
                f"INSERT INTO {table} ({', '.join(columns)}) "
                f"VALUES ({placeholders})", values,
            )
            return cursor.lastrowid
    finally:
        conn.close()


def update_item(table, item_id, data):
    """Изменить существующую запись, вернуть True при успехе."""
    columns = _columns(table)
    values = [data[column] for column in columns]
    set_clause = ", ".join(f"{column} = ?" for column in columns)
    conn = get_connection()
    try:
        with conn:
            cursor = conn.execute(
                f"UPDATE {table} SET {set_clause} WHERE id = ?",
                (*values, item_id),
            )
            return cursor.rowcount > 0
    finally:
        conn.close()


def delete_item(table, item_id):
    """Удалить запись; связанные строки не удаляются автоматически."""
    _columns(table)
    conn = get_connection()
    try:
        try:
            with conn:
                cursor = conn.execute(
                    f"DELETE FROM {table} WHERE id = ?", (item_id,)
                )
                return cursor.rowcount > 0
        except sqlite3.IntegrityError as error:
            raise RelatedRecordsError(
                "Удалить запись нельзя: с ней связаны другие записи. "
                "Сначала удалите или измените связанные задачи и напоминания."
            ) from error
    finally:
        conn.close()
