"""HTTP-тесты: создание, редактирование, удаление, валидация, CSRF."""

import os

import pytest

django = pytest.importorskip("django")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "reminder_site.settings")
django.setup()

from django.test import Client  # noqa: E402
from django.urls import reverse  # noqa: E402
from planner.crud_views import MODELS  # noqa: E402
from django.utils import timezone  # noqa: E402


def get_item(table, item_id):
    return MODELS[table].objects.filter(pk=item_id).values().first()


@pytest.fixture
def web_db(orm_db):
    return Client(), orm_db


@pytest.mark.parametrize("part", [
    "users", "categories", "times", "tasks", "reminders",
])
def test_all_forms_have_buttons_and_csrf(web_db, part):
    client, _ = web_db
    create = client.get(f"/{part}/new/")
    assert create.status_code == 200
    html = create.content.decode("utf-8")
    assert 'name="csrfmiddlewaretoken"' in html
    assert "Сохранить" in html
    assert "Добавить" in client.get(f"/{part}/").content.decode("utf-8")
    assert client.get(f"/{part}/1/edit/").status_code == 200
    assert client.get(f"/{part}/1/delete/").status_code == 200


def test_create_and_edit_all_forms(web_db):
    client, _ = web_db
    records = [
        ("users", "user", {"name": "Саша", "email": "sasha@example.org"}),
        ("categories", "category", {"name": "спорт", "description": "Фитнес"}),
        ("times", "time", {"label": "Утро", "moment": "2026-11-15T08:00"}),
    ]
    created = {}
    for table, singular, payload in records:
        result = client.post(f"/{table}/new/", payload)
        assert result.status_code == 302, result.content.decode("utf-8")
        item_id = (MODELS[table].objects.get(name=payload["name"]).pk
                   if table == "categories" else
                   int(result.url.strip("/").split("/")[-1]))
        created[singular] = item_id
        assert get_item(table, item_id)
    task_data = {
        "title": "Тренировка", "description": "Утром",
        "user_id": created["user"], "category_id": created["category"],
        "status": "COMPLETED",
    }
    response = client.post("/tasks/new/", task_data)
    assert response.status_code == 302
    task_id = int(response.url.strip("/").split("/")[-1])
    reminder_data = {
        "text": "Проснуться", "category_id": created["category"],
        "remind_at": "2026-11-15T08:00", "user_id": created["user"],
        "task_id": task_id, "time_id": created["time"],
    }
    response = client.post("/reminders/new/", reminder_data)
    assert response.status_code == 302, response.content.decode("utf-8")
    reminder_id = int(response.url.strip("/").split("/")[-1])
    assert get_item("reminders", reminder_id)["task_id"] == task_id

    # Редактируем каждую сущность с сохранением связей и проверяем результат.
    changes = [
        (
            "users", created["user"],
            {"name": "Александр", "email": "sasha@example.org"},
            "name", "Александр",
        ),
        (
            "categories", created["category"],
            {"name": "спорт", "description": "Зал"},
            "description", "Зал",
        ),
        (
            "times", created["time"],
            {"label": "Раннее утро", "moment": "2026-11-15T08:00"},
            "label", "Раннее утро",
        ),
        (
            "tasks", task_id, {**task_data, "description": "Спортзал"},
            "description", "Спортзал",
        ),
        (
            "reminders", reminder_id,
            {**reminder_data, "text": "Собираться"},
            "text", "Собираться",
        ),
    ]
    for table, item_id, values, key, value in changes:
        result = client.post(f"/{table}/{item_id}/edit/", values)
        assert result.status_code == 302, result.content.decode("utf-8")
        assert get_item(table, item_id)[key] == value

    for table, item_id in [
        ("reminders", reminder_id), ("tasks", task_id),
        ("times", created["time"]), ("categories", created["category"]),
        ("users", created["user"]),
    ]:
        # GET только показывает подтверждение; никаких side effects.
        assert client.get(f"/{table}/{item_id}/delete/").status_code == 200
        assert get_item(table, item_id) is not None
        assert client.post(f"/{table}/{item_id}/delete/").status_code == 302
        assert get_item(table, item_id) is None


def test_validation_and_relation_guards(web_db):
    client, _ = web_db
    invalid = client.post("/users/new/", {"name": "", "email": "x"})
    assert invalid.status_code == 200
    assert "Сохранить" in invalid.content.decode("utf-8")
    duplicate = client.post("/categories/new/", {
        "name": "учёба", "description": "Дубликат",
    })
    assert duplicate.status_code == 200
    assert "уже существует" in duplicate.content.decode("utf-8")
    mismatched = client.post("/reminders/new/", {
        "text": "Ошибка", "category_id": 3, "remind_at": "2026-11-15T09:00",
        "user_id": 2, "task_id": 1, "time_id": 1,
    })
    assert mismatched.status_code == 200
    assert "должна совпадать" in mismatched.content.decode("utf-8")
    assert client.post("/users/1/delete/").status_code == 409
    assert get_item("users", 1) is not None
    assert client.get("/users/99999/edit/").status_code == 404
    assert client.get("/users/99999/delete/").status_code == 404
    assert client.post("/tasks/1/edit/", {
        "title": "Новое", "description": "", "user_id": 1,
        "category_id": 3,
    }).status_code == 200
    assert get_item("tasks", 1)["category_id"] == 1
    assert client.post("/times/1/edit/", {
        "label": "Новое время", "moment": "2026-12-01T12:00",
    }).status_code == 200
    assert timezone.localtime(get_item("times", 1)["moment"]).strftime(
        "%Y-%m-%dT%H:%M"
    ) == "2026-09-25T14:30"


def test_csrf_required_for_writes(web_db):
    secure = Client(enforce_csrf_checks=True)
    assert secure.post("/users/new/", {
        "name": "Несанкционированный", "email": "no@example.com",
    }).status_code == 403
    assert secure.post("/users/1/delete/").status_code == 403


def test_reversed_named_routes():
    assert reverse("planner:user_create") == "/users/new/"
    assert reverse("planner:task_edit", args=[1]) == "/tasks/1/edit/"
    assert (reverse("planner:reminder_delete", args=[1])
            == "/reminders/1/delete/")
