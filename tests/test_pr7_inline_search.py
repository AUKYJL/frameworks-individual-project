"""ПР7: единый поиск пяти сущностей на SQLite, без Django ORM."""

from db.database import get_connection, load_queries
from db.import_json import import_json


def _rows(conn, name, params):
    return conn.execute(load_queries()[name], params).fetchall()


def test_inline_search_queries(tmp_path):
    path = tmp_path / "inline.sqlite"
    import_json(path)
    conn = get_connection(path)
    try:
        users = _rows(conn, "search_users", ("Илья", "Илья", "Илья"))
        assert [x["name"] for x in users] == ["Илья"]
        users = _rows(conn, "search_users", ("anna@", "anna@", "anna@"))
        assert [x["name"] for x in users] == ["Анна"]

        categories = _rows(conn, "search_categories", (
            "Занятия", "Занятия", "Занятия",
        ))
        assert [x["name"] for x in categories] == ["учёба"]

        times = _rows(conn, "search_times", (
            "", "", "1000-01-27", "1000-01-27",
        ))
        assert len(times) == 1 and times[0]["label"] == "Рабочее напоминание"
        assert not _rows(conn, "search_times", (
            "Рабочее", "Рабочее", "2026-01-01", "2026-01-01",
        ))

        done_tasks = _rows(conn, "search_tasks", (
            "", "", "", "done", 1, 0, 0,
        ))
        assert done_tasks and all(row["is_completed"] for row in done_tasks)
        category_tasks = _rows(conn, "search_tasks", (
            "домаш", "домаш", "домаш", "all", 0, 1, 1,
        ))
        assert category_tasks
        assert all(row["category_id"] == 1 for row in category_tasks)

        matches = _rows(conn, "search_reminders_filtered", (
            "домаш", "домаш", 1, 1, "", "", "all", "2026-10-22T10:00",
            "2026-10-22T10:00", "all",
        ))
        assert len(matches) == 1 and matches[0]["id"] == 1
        overdue = _rows(conn, "search_reminders_filtered", (
            "", "", 0, 0, "", "", "overdue", "2026-10-22T10:00",
            "2026-10-22T10:00", "overdue",
        ))
        assert len(overdue) == 2
        before = _rows(conn, "search_reminders_filtered", (
            "", "", 0, 0, "1000-12-31", "1000-12-31T23:59:59",
            "all", "2026-10-22T10:00", "2026-10-22T10:00", "all",
        ))
        assert [row["text"] for row in before] == ["йцу"]
    finally:
        conn.close()


def test_inline_search_prevents_sql_injection(tmp_path):
    path = tmp_path / "inline.sqlite"
    import_json(path)
    conn = get_connection(path)
    try:
        injection = "' OR 1=1 --"
        assert _rows(conn, "search_users", (
            injection, injection, injection,
        )) == []
        assert not _rows(conn, "search_tasks", (
            injection, injection, injection, "all", 0, 0, 0,
        ))
        assert conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 3
    finally:
        conn.close()
