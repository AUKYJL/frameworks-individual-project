"""CRUD-операции sqlite3: связи, транзакции и сохранение."""

import sqlite3
from unittest.mock import patch

import pytest

from db.crud import (RelatedRecordsError, delete_item, get_item,
                     insert_item, update_item)
from db.database import get_connection
from db.import_json import import_json


@pytest.fixture
def sqlite_db(tmp_path):
    path = tmp_path / "crud.sqlite"
    import_json(path)
    with patch("db.database.DB_PATH", path):
        yield path


def test_create_update_delete_each_entity(sqlite_db):
    new_user = insert_item("users", {
        "name": "Мария", "email": "maria@example.com",
    })
    new_category = insert_item("categories", {
        "name": "спорт", "description": "Тренировки",
    })
    new_time = insert_item("times", {
        "label": "Вечер", "moment": "2026-11-10T19:00",
    })
    new_task = insert_item("tasks", {
        "title": "Пробежка", "description": "В парке", "user_id": new_user,
        "category_id": new_category, "is_completed": 0,
    })
    new_reminder = insert_item("reminders", {
        "text": "Выйти из дома", "category_id": new_category,
        "remind_at": "2026-11-10T19:00", "user_id": new_user,
        "task_id": new_task, "time_id": new_time,
    })
    assert get_item("reminders", new_reminder)["task_id"] == new_task
    assert update_item("users", new_user, {
        "name": "Мария Новая", "email": "maria@example.com",
    })
    assert update_item("categories", new_category, {
        "name": "спорт", "description": "Обновлено",
    })
    assert update_item("times", new_time, {
        "label": "Вечернее время", "moment": "2026-11-10T19:00",
    })
    assert update_item("tasks", new_task, {
        "title": "Пробежка", "description": "Вокруг парка",
        "user_id": new_user,
        "category_id": new_category, "is_completed": 1,
    })
    assert update_item("reminders", new_reminder, {
        "text": "Надеть кроссовки", "category_id": new_category,
        "remind_at": "2026-11-10T19:00", "user_id": new_user,
        "task_id": new_task, "time_id": new_time,
    })
    assert get_item("reminders", new_reminder)["text"] == "Надеть кроссовки"
    assert get_item("tasks", new_task)["is_completed"] == 1
    assert get_item("categories", new_category)["description"] == "Обновлено"
    for table, key in (
        ("reminders", new_reminder), ("tasks", new_task),
        ("times", new_time), ("categories", new_category),
        ("users", new_user),
    ):
        assert delete_item(table, key)
        assert get_item(table, key) is None


def test_delete_refused_for_related_records(sqlite_db):
    for table, key in (("users", 1), ("categories", 1),
                       ("times", 1), ("tasks", 1)):
        with pytest.raises(RelatedRecordsError):
            delete_item(table, key)
        assert get_item(table, key) is not None
    assert delete_item("reminders", 1)
    assert get_item("reminders", 1) is None


def test_unique_constraints_and_rollback(sqlite_db):
    with pytest.raises(sqlite3.IntegrityError):
        insert_item("users", {
            "name": "Вторая Анна", "email": "anna@example.com"
        })
    with pytest.raises(sqlite3.IntegrityError):
        update_item("users", 1, {"name": "Анна", "email": "ilya@example.com"})
    assert get_item("users", 1)["email"] == "anna@example.com"
    with pytest.raises(sqlite3.IntegrityError):
        insert_item("tasks", {
            "title": "Сирота", "description": "", "user_id": 999999,
            "category_id": 1, "is_completed": 0,
        })
    conn = get_connection()
    try:
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
    finally:
        conn.close()


def test_sql_injection_does_not_change_schema(sqlite_db):
    evil = "x'); DROP TABLE users; --"
    key = insert_item("categories", {"name": evil, "description": "test"})
    assert get_item("categories", key)["name"] == evil
    conn = get_connection()
    try:
        assert conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 2
    finally:
        conn.close()


def test_invalid_table_names_rejected(sqlite_db):
    with pytest.raises(ValueError):
        delete_item("users; DROP TABLE categories", 1)
    with pytest.raises(ValueError):
        get_item("unknown", 1)
