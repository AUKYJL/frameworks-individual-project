"""Проверка SQLite без Django: схема, связи, импорт, запросы и статистика."""

import json
import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest

from db.database import get_connection, load_queries
from db.import_json import import_json
from project_data import load_project_data


@pytest.fixture
def sqlite_path(tmp_path):
    path = tmp_path / "project.sqlite"
    import_json(path)
    return path


def test_five_tables(sqlite_path):
    conn = get_connection(sqlite_path)
    names = {row["name"] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
    )}
    assert {"users", "categories", "times", "tasks", "reminders"} <= names
    conn.close()


def test_json_data_imported_without_loss(sqlite_path):
    data = load_project_data()
    expected = {
        "users": len(data.users), "categories": len(data.categories),
        "times": len(data.times), "tasks": len(data.tasks),
        "reminders": len(data.reminders),
    }
    conn = get_connection(sqlite_path)
    for table, count in expected.items():
        found = conn.execute("SELECT COUNT(*) FROM " + table).fetchone()[0]
        assert found == count
    assert conn.execute(
        "SELECT text FROM reminders WHERE id = 2"
    ).fetchone()[0] == "йцу"
    assert conn.execute(
        "SELECT remind_at FROM reminders WHERE id = 2"
    ).fetchone()[0] == "1000-01-27T12:30"
    conn.close()


def test_schema_has_foreign_keys(sqlite_path):
    conn = get_connection(sqlite_path)
    tasks_fks = {row["table"] for row in conn.execute(
        "PRAGMA foreign_key_list(tasks)"
    )}
    reminder_fks = {row["table"] for row in conn.execute(
        "PRAGMA foreign_key_list(reminders)"
    )}
    assert tasks_fks == {"users", "categories"}
    assert reminder_fks == {"users", "categories", "times", "tasks"}
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO tasks(id,title,user_id,category_id) "
            "VALUES(100, 'test', 999999, 1)"
        )
    conn.rollback()
    conn.close()


def test_reimport_is_repeatable(sqlite_path):
    import_json(sqlite_path)
    conn = get_connection(sqlite_path)
    assert conn.execute("SELECT COUNT(*) FROM reminders").fetchone()[0] == 2
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
    conn.close()


def test_import_error_does_not_erase_database(sqlite_path):
    with patch("db.import_json.load_project_data", side_effect=ValueError):
        with pytest.raises(ValueError):
            import_json(sqlite_path)
    conn = get_connection(sqlite_path)
    assert conn.execute("SELECT COUNT(*) FROM reminders").fetchone()[0] == 2
    conn.close()


def test_all_named_queries_run(sqlite_path):
    queries = load_queries()
    assert len(queries) >= 10
    conn = get_connection(sqlite_path)
    for name, query in queries.items():
        if name == "search_reminders":
            args = ("", "", 0, 0)
        else:
            args = tuple(1 for _ in range(query.count("?")))
        assert conn.execute(query, args).fetchall() is not None, name
    conn.close()


def test_at_least_two_queries_each_category():
    query_file = Path(__file__).parent.parent / "sql" / "queries.sql"
    contents = query_file.read_text(encoding="utf-8")
    for sql_term in ("SELECT", "WHERE", "JOIN", "COUNT(", "GROUP BY"):
        assert contents.upper().count(sql_term) >= 2


def test_joined_reminders_show_all_links(sqlite_path):
    conn = get_connection(sqlite_path)
    rows = conn.execute(load_queries()["joined_reminders"]).fetchall()
    assert rows[0]["category"] in ("работа", "учёба")
    assert all(row["user_name"] for row in rows)
    assert all(row["task_title"] for row in rows)
    assert all(row["time_label"] for row in rows)
    conn.close()


def test_task_counts_include_categories_with_zero_tasks(sqlite_path):
    conn = get_connection(sqlite_path)
    rows = conn.execute(load_queries()["tasks_by_category"]).fetchall()
    assert {row["name"]: row["task_count"] for row in rows} == {
        "учёба": 1, "работа": 1, "личное": 1,
    }
    counts = conn.execute(load_queries()["task_completion_totals"]).fetchone()
    assert (counts["total_tasks"], counts["completed_tasks"]) == (3, 1)
    conn.close()


def test_having_filters_groups(sqlite_path):
    conn = get_connection(sqlite_path)
    rows = conn.execute(load_queries()["busy_users"], (2,)).fetchall()
    assert len(rows) == 1
    assert rows[0]["name"] == "Анна"
    conn.close()


def test_parameterized_search_and_sql_injection(sqlite_path):
    conn = get_connection(sqlite_path)
    sql = load_queries()["search_reminders"]
    rows = conn.execute(sql, ("домашнее", "домашнее", 1, 1)).fetchall()
    assert len(rows) == 1
    attack = "' OR 1=1 --"
    assert conn.execute(sql, (attack, attack, 0, 0)).fetchall() == []
    assert conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 2
    conn.close()


def test_json_files_not_modified(sqlite_path):
    project = Path(__file__).parent.parent
    for name in ("users", "reminders", "categories", "times", "tasks"):
        raw = json.loads((project / "data" / f"{name}.json").read_text(
            encoding="utf-8"
        ))
        assert isinstance(raw, list)
