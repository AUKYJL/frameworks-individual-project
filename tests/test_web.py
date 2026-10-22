"""HTTP-проверки ПР5 (требуется установка Django из requirements)."""

import os

import pytest

django = pytest.importorskip("django")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "reminder_site.settings")
django.setup()

from django.test import Client, override_settings  # noqa: E402


@pytest.mark.parametrize("url,expected", [
    ("/", "Сервис напоминаний"),
    ("/reminders/", "Напоминания"),
    ("/reminders/1/", "Подготовить домашнее задание"),
    ("/users/", "Пользователи"),
    ("/users/1/", "anna@example.com"),
    ("/categories/", "Категории"),
    ("/categories/1/", "Занятия и домашние задания"),
    ("/times/", "Планируемые моменты"),
    ("/times/1/", "2026"),
    ("/tasks/", "Задачи"),
    ("/tasks/1/", "Сделать домашнее задание"),
])
def test_get_pages(url, expected):
    response = Client().get(url)
    assert response.status_code == 200
    assert expected in response.content.decode("utf-8")


@pytest.mark.parametrize("name", [
    "reminders", "users", "categories", "times", "tasks",
])
def test_unknown_object_returns_404(name):
    response = Client().get(f"/{name}/9999/")
    assert response.status_code == 404
    assert "не найден" in response.content.decode("utf-8")


@override_settings(DEBUG=False)
def test_unknown_route_uses_custom_404():
    response = Client().get("/not-a-real-page/")
    assert response.status_code == 404
    assert "Вернитесь" in response.content.decode("utf-8") or (
        "вернитесь" in response.content.decode("utf-8")
    )


def test_project_has_only_read_only_pages():
    response = Client().post("/reminders/", {"text": "не добавлять"})
    assert response.status_code == 405  # изменения через HTTP ещё не изучались
