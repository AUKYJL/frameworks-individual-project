"""ПР10: статусы, вычисляемое поле, slug и сохранение данных миграциями."""

import re
import sqlite3
from datetime import datetime
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connections, models
from django.db.migrations.executor import MigrationExecutor
from django.test import Client
from django.utils import timezone

from planner.forms import TaskForm
from planner.models import Category, Reminder, Task


@pytest.mark.usefixtures("orm_db")
@pytest.mark.parametrize("status", Task.Status.values)
def test_status_crud_and_generated_column(status):
    payload = {
        "title": "Новая задача", "user": 1, "category": 1,
        "status": status,
    }
    client = Client()
    result = client.post("/tasks/new/", payload)
    assert result.status_code == 302
    task = Task.objects.get(title=payload["title"])
    assert task.status == status
    assert task.is_completed == (status == Task.Status.COMPLETED)
    for next_status in Task.Status:
        result = client.post(f"/tasks/{task.pk}/edit/", {
            **payload, "status": next_status,
        })
        assert result.status_code == 302
        task.refresh_from_db()
        assert task.status == next_status
        assert task.is_completed == (next_status == Task.Status.COMPLETED)
    # UPDATE без save() тоже пересчитывает колонку в самой БД.
    Task.objects.filter(pk=task.pk).update(status=Task.Status.COMPLETED)
    task.refresh_from_db()
    assert task.is_completed is True
    field = Task._meta.get_field("is_completed")
    assert isinstance(field, models.GeneratedField) and field.db_persist
    assert "is_completed" not in TaskForm().fields
    invalid = TaskForm({**payload, "status": "INVALID"})
    assert not invalid.is_valid() and "status" in invalid.errors


@pytest.mark.usefixtures("orm_db")
def test_queryset_date_chaining_filters_and_statistics():
    for pk, status in enumerate(Task.Status, start=1):
        Task.objects.filter(pk=pk).update(status=status)
    for method, status in [
        ("active", Task.Status.ACTIVE), ("completed", Task.Status.COMPLETED),
        ("cancelled", Task.Status.CANCELLED),
    ]:
        assert list(getattr(Task.objects, method)().values_list(
            "status", flat=True,
        )) == [status]
    Reminder.objects.all().delete()
    # В Москве уже 20-е, в UTC ещё 19-е; два напоминания не дублируют задачу.
    moment = timezone.make_aware(datetime(2026, 11, 20, 0, 30))
    for _ in range(2):
        Reminder.objects.create(
            text="Дата", category_id=1, task_id=1, remind_at=moment,
        )
    assert list(Task.objects.active().for_date(moment.date()).values_list(
        "pk", flat=True,
    )) == [1]
    assert not Task.objects.for_date("2026-11-19").exists()
    client = Client()
    for value, status in [("open", Task.Status.ACTIVE),
                          ("done", Task.Status.COMPLETED),
                          ("cancelled", Task.Status.CANCELLED)]:
        response = client.get("/tasks/", {"status": value})
        assert [e["task"].status
                for e in response.context["entries"]] == [status]
    assert "Отменено" in client.get("/tasks/3/").content.decode()
    totals = client.get("/statistics/").context["totals"]
    assert totals == {
        "total_tasks": 3, "open_tasks": 1,
        "completed_tasks": 1, "cancelled_tasks": 1,
    }


@pytest.mark.usefixtures("orm_db")
def test_slug_generation_collisions_stability_and_urls():
    names = ["Новая категория", "Novaya kategoriya",
             "!!!", "???", "123", "new",
             "я" * 100, "ya" * 100]
    categories = [Category.objects.create(name=name) for name in names]
    slugs = [category.slug for category in categories]
    assert slugs[:2] == ["novaya-kategoriya", "novaya-kategoriya-2"]
    assert len(set(slugs)) == len(slugs)
    client = Client()
    for category in categories:
        assert re.fullmatch(r"[a-z0-9-]{1,120}", category.slug)
        for url in [category.get_absolute_url(),
                    f"/categories/{category.pk}/"]:
            response = client.get(url)
            assert response.status_code == 200
            assert response.context["category"].pk == category.pk
    category = categories[0]
    previous = category.get_absolute_url()
    result = client.post(f"/categories/{category.pk}/edit/", {
        "name": "Другое название", "description": "Описание",
    })
    assert result.url == previous
    category.refresh_from_db()
    assert category.get_absolute_url() == previous
    assert previous in client.get("/categories/").content.decode()
    assert client.get("/categories/missing-slug/").status_code == 404
    assert client.get("/categories/new/").status_code == 200


@pytest.mark.usefixtures("orm_db")
def test_import_does_not_overwrite_cancelled_status(orm_db):
    Task.objects.filter(pk=1).update(status=Task.Status.CANCELLED)
    with pytest.raises(CommandError, match="Конфликт tasks"):
        call_command("import_pr7", source=orm_db, stdout=StringIO())
    assert Task.objects.get(pk=1).status == Task.Status.CANCELLED
    # Невалидное значение исходного bool не должно превращаться в статус.
    with sqlite3.connect(orm_db) as source:
        source.execute("PRAGMA ignore_check_constraints = ON")
        source.execute("UPDATE tasks SET is_completed=2 WHERE id=1")
    with pytest.raises(CommandError, match="Некорректный статус"):
        call_command("import_pr7", source=orm_db, stdout=StringIO())


def test_migrations_preserve_old_data_and_relations(tmp_path, orm_database):
    alias = "pr10_migration_test"
    connections.databases[alias] = {
        **connections["default"].settings_dict,
        "NAME": str(tmp_path / "migration.sqlite3"),
    }
    connection = connections[alias]
    old = [("planner", "0001_initial")]
    latest = [("planner", "0005_admin_localization")]
    try:
        executor = MigrationExecutor(connection)
        executor.migrate(old)
        apps = executor.loader.project_state(old).apps
        user = apps.get_model("planner", "User").objects.using(alias).create(
            name="Тест", email="migration@example.org",
        )
        categories = apps.get_model("planner", "Category").objects.using(alias)
        category = categories.create(name="Учёба", description="Сохранить")
        categories.create(name="Uchyoba")
        tasks = apps.get_model("planner", "Task").objects.using(alias)
        for completed in [False, True]:
            tasks.create(title=str(completed), user_id=user.pk,
                         category_id=category.pk, is_completed=completed)
        moment = timezone.make_aware(datetime(2026, 11, 20, 10))
        time = apps.get_model("planner", "Time").objects.using(alias).create(
            label="Время", moment=moment,
        )
        reminders = apps.get_model("planner", "Reminder").objects.using(alias)
        reminder = reminders.create(
            text="Связи", category_id=category.pk, user_id=user.pk,
            task_id=1, time_id=time.pk, remind_at=moment,
        )
        executor = MigrationExecutor(connection)
        executor.migrate(latest)
        apps = executor.loader.project_state(latest).apps
        rows = apps.get_model("planner", "Task").objects.using(alias)
        assert list(rows.order_by("id").values_list(
            "status", "is_completed",
        )) == [
            ("ACTIVE", False), ("COMPLETED", True),
        ]
        categories = apps.get_model("planner", "Category").objects.using(alias)
        assert list(categories.order_by("id").values_list(
            "slug", flat=True,
        )) == [
            "uchyoba", "uchyoba-2",
        ]
        assert categories.get(pk=category.pk).description == "Сохранить"
        reminders = apps.get_model("planner", "Reminder").objects.using(alias)
        stored = reminders.get(
            pk=reminder.pk,
        )
        assert (stored.user_id, stored.task_id, stored.category_id,
                stored.time_id,
                stored.remind_at) == (user.pk, 1, category.pk, time.pk, moment)
        with connection.cursor() as cursor:
            cursor.execute("PRAGMA table_xinfo(planner_task)")
            assert any(row[1] == "is_completed" and row[6] == 3
                       for row in cursor.fetchall())
        executor = MigrationExecutor(connection)
        executor.migrate(old)
        apps = executor.loader.project_state(old).apps
        rows = apps.get_model("planner", "Task").objects.using(alias)
        assert list(rows.order_by("id").values_list(
            "is_completed", flat=True,
        )) == [
            False, True,
        ]
        MigrationExecutor(connection).migrate(latest)
    finally:
        connection.close()
        del connections[alias]
        del connections.databases[alias]


@pytest.mark.usefixtures("orm_db")
def test_task_filters_combine_status_date_user_category_without_duplicates():
    from planner.models import User

    Reminder.objects.all().delete()
    moment = timezone.make_aware(datetime(2026, 11, 20, 0, 30))
    other_user = User.objects.create(name="Другой", email="other@example.org")
    other_category = Category.objects.create(name="Другая")
    matching = None
    for status, user_id, category_id in [
        (Task.Status.ACTIVE, 1, 1),
        (Task.Status.COMPLETED, 1, 1),
        (Task.Status.CANCELLED, 1, 1),
        (Task.Status.ACTIVE, other_user.pk, 1),
        (Task.Status.ACTIVE, 1, other_category.pk),
    ]:
        task = Task.objects.create(
            title="Фильтр", status=status, user_id=user_id,
            category_id=category_id,
        )
        for _ in range(2):
            Reminder.objects.create(
                text="Дата", task=task, user_id=user_id,
                category_id=category_id, remind_at=moment,
            )
        if matching is None:
            matching = task
    params = {"q": "Фильтр", "status": "open", "day": "2026-11-20",
              "user": "1", "category": "1"}
    client = Client()
    response = client.get("/tasks/", params)
    assert response.status_code == 200
    assert [e["task"].pk for e in response.context["entries"]] == [matching.pk]
    assert 'value="2026-11-20"' in response.content.decode()
    assert client.get("/tasks/", {**params, "day": "2026-11-19"}).context[
        "entries"
    ] == []
    invalid = client.get("/tasks/", {
        **params, "day": "2026-02-30", "user": "9" * 5000,
    })
    assert invalid.status_code == 200
    assert invalid.context["date_error"]
    assert invalid.context["selected_user"] == 0


@pytest.mark.usefixtures("orm_db")
@pytest.mark.parametrize("field", ["text", "category", "user"])
def test_reminder_search_matches_each_q_branch(field):
    from planner.models import User

    Reminder.objects.all().delete()
    category = Category.objects.create(name="Категория поиска")
    user = User.objects.create(name="Имя поиска", email="search@example.org")
    reminder = Reminder.objects.create(
        text="Текст поиска", category=category, user=user,
        remind_at=timezone.now(),
    )
    query = {"text": "Текст поиска", "category": category.name,
             "user": user.name}[field]
    response = Client().get("/reminders/", {"q": query})
    entries = response.context["entries"]
    assert [e["reminder"]["id"] for e in entries] == [reminder.pk]
    assert entries[0]["reminder"]["user_name"] == user.name
    assert entries[0]["reminder"]["category_name"] == category.name
    assert Client().get("/reminders/", {
        "q": query, "category": 1,
    }).context["entries"] == []


@pytest.mark.usefixtures("orm_db")
def test_reminder_values_query_and_single_pagination_preserve_filters():
    from datetime import timedelta
    from html import unescape
    from unittest.mock import patch
    from urllib.parse import parse_qs

    from django.db import connection
    from django.test.utils import CaptureQueriesContext

    Reminder.objects.all().delete()
    category = Category.objects.create(name="Общий поиск")
    moment = timezone.make_aware(datetime(2026, 11, 20, 0, 30))
    for index in range(7):
        Reminder.objects.create(
            text=f"Запись {index}", category=category,
            remind_at=moment + timedelta(minutes=index),
        )
    params = {"q": category.name, "category": str(category.pk),
              "before": "2026-11-20", "status": "upcoming", "sort": "-date"}
    now = moment - timedelta(days=1)
    with patch("planner.views.timezone.now", return_value=now):
        with CaptureQueriesContext(connection) as captured:
            first = Client().get("/reminders/", params)
        queries = captured.captured_queries
        second = Client().get("/reminders/", {**params, "page": 2})
    rows = first.context["entries"]
    assert isinstance(rows[0]["reminder"], dict)
    assert rows[0]["reminder"]["text"] == "Запись 6"
    assert rows[0]["reminder"]["user_name"] is None
    assert len(rows) == 5 and len(second.context["entries"]) == 2
    assert not ({e["reminder"]["id"] for e in rows} & {
        e["reminder"]["id"] for e in second.context["entries"]
    })
    # Список, два COUNT, варианты категорий и валидация ModelChoiceField.
    assert len(queries) == 5
    row_queries = [
        q["sql"] for q in queries if 'AS "category_name"' in q["sql"]
    ]
    assert len(row_queries) == 1 and 'AS "user_name"' in row_queries[0]
    html = first.content.decode()
    assert html.count('aria-label="Страницы напоминаний"') == 1
    title = re.search(r"<title>(.*?)</title>", html, re.S).group(1)
    assert "<nav" not in title
    href = re.search(r'href="(\?[^\"]*page=2)"', html).group(1)
    assert parse_qs(unescape(href)[1:]) == {
        **{key: [value] for key, value in params.items()}, "page": ["2"],
    }
    assert "20.11.2026 00:36" in html
    assert category.name in html


@pytest.mark.usefixtures("orm_db")
def test_shared_context_counts_and_category_links():
    client = Client()
    for url in ["/", "/tasks/", "/categories/", "/statistics/"]:
        response = client.get(url)
        assert response.context["service_name"] == "Reminderly"
        assert response.context["reminder_count"] == Reminder.objects.count()
        html = response.content.decode()
        assert "ПР11" in html and "ПР10" not in html and "ПР7" not in html
    category = Category.objects.get(pk=1)
    for url in ["/categories/", "/tasks/1/", "/reminders/1/"]:
        assert f'href="{category.get_absolute_url()}"' in client.get(
            url,
        ).content.decode()
    Reminder.objects.all().delete()
    assert client.get("/tasks/").context["reminder_count"] == 0
    Task.objects.all().delete()
    totals = client.get("/statistics/").context["totals"]
    assert totals == dict.fromkeys([
        "total_tasks", "open_tasks", "completed_tasks", "cancelled_tasks",
    ], 0)


@pytest.mark.usefixtures("orm_db")
@pytest.mark.parametrize("url,object_name,relations", [
    ("/reminders/1/", "reminder", ("category", "user", "task", "time")),
    ("/tasks/1/", "task", ("category", "user")),
])
def test_detail_relations_remain_eagerly_loaded(url, object_name, relations):
    from django.db import connection
    from django.test.utils import CaptureQueriesContext

    record = Client().get(url).context[object_name]
    with CaptureQueriesContext(connection) as queries:
        for relation in relations:
            assert getattr(record, relation) is not None
    assert len(queries) == 0
