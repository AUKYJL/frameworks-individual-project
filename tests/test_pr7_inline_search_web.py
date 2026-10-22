"""Демонстрация поисковых форм прямо на страницах списков."""

import os
from unittest.mock import patch

import pytest

django = pytest.importorskip("django")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "reminder_site.settings")
django.setup()

from django.test import Client  # noqa: E402
from db.import_json import import_json  # noqa: E402


@pytest.fixture
def web_db(tmp_path):
    db_path = tmp_path / "web_search.sqlite"
    import_json(db_path)
    with patch("db.database.DB_PATH", db_path):
        yield Client()


@pytest.mark.parametrize("path", [
    "/reminders/", "/tasks/", "/users/", "/categories/", "/times/",
])
def test_inline_search_forms(web_db, path):
    response = web_db.get(path)
    assert response.status_code == 200
    html = response.content.decode("utf-8")
    assert 'type="search"' in html
    assert 'name="q"' in html
    assert 'method="get"' in html


def test_inline_search_queries_and_preserved_values(web_db):
    response = web_db.get('/users/?q=ilya%40example.com')
    assert response.status_code == 200
    response = web_db.get('/users/?q=anna%40example.com')
    assert "Анна" in response.content.decode("utf-8")
    assert "Илья" not in response.content.decode("utf-8")

    html = web_db.get(
        "/tasks/?q=домаш&status=open&category=1"
    ).content.decode("utf-8")
    assert 'value="домаш"' in html
    assert "Сделать домашнее задание" in html
    assert "Купить продукты" not in html

    html = web_db.get('/reminders/?q=домаш&category=1').content.decode("utf-8")
    assert "Подготовить домашнее задание" in html
    assert "йцу" not in html

    html = web_db.get('/times/?day=1000-01-27').content.decode("utf-8")
    assert "Рабочее напоминание" in html
    assert "Домашнее задание" not in html


def test_old_search_url_keeps_working(web_db):
    response = web_db.get('/search/?q=домаш')
    assert response.status_code == 200
    assert "Подготовить домашнее задание" in response.content.decode("utf-8")
    assert 'action="/reminders/"' in response.content.decode("utf-8")
