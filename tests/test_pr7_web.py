"""ПР7: HTTP-страницы действительно получают данные из SQLite."""

import os
from unittest.mock import patch

import pytest

django = pytest.importorskip("django")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "reminder_site.settings")
django.setup()

from django.test import Client  # noqa: E402
from db.database import get_connection  # noqa: E402
from db.import_json import import_json  # noqa: E402


@pytest.fixture
def client_db(tmp_path):
    path = tmp_path / "test.sqlite"
    import_json(path)
    with patch("db.database.DB_PATH", path):
        yield Client(), path


@pytest.mark.parametrize("url", [
    "/", "/reminders/", "/reminders/1/", "/tasks/", "/tasks/1/",
    "/users/", "/users/1/", "/categories/", "/categories/1/",
    "/times/", "/times/1/", "/search/", "/statistics/",
])
def test_sqlite_pages_return_200(client_db, url):
    client, _ = client_db
    assert client.get(url).status_code == 200


def test_changes_in_sqlite_are_visible_without_json_edits(client_db):
    client, path = client_db
    conn = get_connection(path)
    with conn:
        conn.execute("UPDATE reminders SET text = ? WHERE id = 1", (
            "Изменено непосредственно в SQLite",))
    conn.close()
    assert "Изменено непосредственно в SQLite" in (
        client.get("/reminders/").content.decode("utf-8")
    )


def test_search_and_status_filters(client_db):
    client, _ = client_db
    html = client.get("/search/?q=домашнее&category=1").content.decode(
        "utf-8"
    )
    assert "Подготовить домашнее задание" in html
    html = client.get("/tasks/?status=done").content.decode("utf-8")
    assert "Купить продукты" in html
    assert "Сделать домашнее задание" not in html
    html = client.get("/search/?before=1000-12-31").content.decode("utf-8")
    assert "Подготовить домашнее задание" not in html
    assert "йцу" in html


def test_statistics_have_aggregates(client_db):
    client, _ = client_db
    response = client.get("/statistics/?min_tasks=2")
    assert response.status_code == 200
    html = response.content.decode("utf-8")
    assert "Выполнено задач" in html
    assert "Анна" in html


def test_missing_entity_and_missing_db(client_db):
    client, path = client_db
    assert client.get("/reminders/999999/").status_code == 404
    path.unlink()
    response = Client(raise_request_exception=False).get("/tasks/")
    assert response.status_code == 500


def test_search_is_read_only_and_handles_injection(client_db):
    client, _ = client_db
    assert client.get('/search/?q=%27+OR+1%3D1+--').status_code == 200
    assert client.post('/search/', {'q': 'test'}).status_code == 405
