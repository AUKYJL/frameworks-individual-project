"""ПР9: перенос, ORM-статистика, сортировка, пагинация и часовые пояса."""

import hashlib
import sqlite3
from datetime import datetime, timedelta
from io import StringIO
from unittest.mock import patch
from urllib.parse import parse_qs

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import DatabaseError
from django.db.models.deletion import ProtectedError
from django.test import Client, override_settings
from django.utils import timezone

from planner.forms import ReminderForm
from planner.models import Category, Reminder, Task, Time, User

pytestmark = pytest.mark.usefixtures("orm_db")


def test_transfer_values_ids_relations_and_read_only_source(orm_db):
    before = hashlib.sha256(orm_db.read_bytes()).hexdigest()
    output = StringIO()
    call_command("import_pr7", source=orm_db, stdout=output)
    assert output.getvalue().count("создано 0") == 5
    assert hashlib.sha256(orm_db.read_bytes()).hexdigest() == before
    with sqlite3.connect(orm_db) as conn:
        conn.row_factory = sqlite3.Row
        for table, model in (
            ("users", User), ("categories", Category), ("times", Time),
            ("tasks", Task), ("reminders", Reminder),
        ):
            rows = conn.execute(f"SELECT * FROM {table}").fetchall()
            assert model.objects.count() == len(rows)
            for row in rows:
                record = model.objects.get(pk=row["id"])
                for key, expected in dict(row).items():
                    value = getattr(record, key)
                    if isinstance(value, datetime):
                        value = timezone.localtime(value).isoformat(
                            timespec="minutes",
                        )[:16]
                    assert value == expected
    assert Reminder.objects.get(pk=1).task.user.pk == 1


def test_transfer_conflict_rolls_back_all_tables(orm_db):
    # Новая запись в первой таблице не должна пережить конфликт в последней.
    with sqlite3.connect(orm_db) as conn:
        conn.execute(
            "INSERT INTO users VALUES (99, 'New', 'new@example.org')",
        )
    Reminder.objects.filter(pk=1).update(text="Изменено через ORM")
    with pytest.raises(CommandError, match="Конфликт reminders"):
        call_command("import_pr7", source=orm_db, stdout=StringIO())
    assert not User.objects.filter(pk=99).exists()
    assert Reminder.objects.get(pk=1).text == "Изменено через ORM"


def test_transfer_unique_conflict_is_not_silently_skipped(orm_db):
    User.objects.create(pk=99, name="Other", email="taken@example.org")
    with sqlite3.connect(orm_db) as conn:
        conn.execute(
            "INSERT INTO users VALUES (100, 'New', 'taken@example.org')",
        )
    with pytest.raises(CommandError, match="Перенос отменён"):
        call_command("import_pr7", source=orm_db, stdout=StringIO())
    assert not User.objects.filter(pk=100).exists()


def test_missing_source_is_not_created(tmp_path):
    path = tmp_path / "missing.sqlite"
    with pytest.raises(CommandError):
        call_command("import_pr7", source=path)
    assert not path.exists()


@pytest.mark.parametrize("model", [User, Category, Task, Time])
def test_protect_related_records(model):
    with pytest.raises(ProtectedError):
        model.objects.get(pk=1).delete()
    assert model.objects.filter(pk=1).exists()


def test_optional_relations_and_boolean():
    reminder = Reminder.objects.create(
        text="Без необязательных связей", category_id=1,
        remind_at=timezone.now(),
    )
    assert reminder.user is reminder.task is reminder.time is None
    assert isinstance(Task.objects.get(pk=1).is_completed, bool)
    assert User._meta.label == "planner.User"


def test_sorting_pagination_preserve_all_parameters():
    moment = timezone.make_aware(datetime(2026, 11, 1, 12))
    for index in range(12):
        Reminder.objects.create(
            text=f"Проверка {index}", category_id=1,
            remind_at=moment + timedelta(days=index),
        )
    params = {
        "q": "Проверка", "category": "1", "before": "2026-12-31",
        "status": "upcoming", "sort": "-date",
    }
    now = timezone.make_aware(datetime(2026, 10, 27, 12))
    with patch("planner.views.timezone.now", return_value=now):
        response = Client().get("/reminders/", params)
        context = response.context
        assert context["page_obj"].paginator.count == 12
        assert len(context["entries"]) == 5
        assert context["entries"][0]["reminder"]["text"] == "Проверка 11"
        assert parse_qs(context["page_query"]) == {
            key: [value] for key, value in params.items()
        }
        assert "page=2" in response.content.decode()
        second = Client().get("/reminders/", {**params, "page": 2})
        first_ids = {e["reminder"]["id"] for e in context["entries"]}
        second_ids = {e["reminder"]["id"] for e in second.context["entries"]}
        assert not first_ids & second_ids
        last = Client().get("/reminders/", {**params, "page": 9999})
        assert last.context["page_obj"].number == 3
        assert len(last.context["entries"]) == 2
    by_category = Client().get("/reminders/?sort=category")
    names = [e["reminder"]["category_name"]
             for e in by_category.context["entries"]]
    assert names == sorted(names)


@pytest.mark.parametrize("params", [
    {"page": "wrong", "sort": "DROP TABLE"},
    {"page": "-1", "category": "oops", "status": "bad"},
    {"page": "9" * 5000, "category": "9" * 5000},
    {"before": "2026-02-30"},
])
def test_bad_list_parameters(params):
    response = Client().get("/reminders/", params)
    assert response.status_code == 200
    assert response.context["sort"] == "date"
    assert response.context["page_obj"].number == 1


def test_min_tasks_handles_huge_value():
    response = Client().get("/statistics/", {"min_tasks": "9" * 5000})
    assert response.status_code == 200
    assert response.context["min_tasks"] == 100


def test_status_matches_minute_filters_and_local_date():
    Reminder.objects.all().delete()
    now = timezone.make_aware(datetime(2026, 10, 28, 0, 0, 30))
    moments = [("overdue", -60), ("current", 20), ("upcoming", 60)]
    for label, delta in moments:
        Reminder.objects.create(
            text=label, category_id=1,
            remind_at=now + timedelta(seconds=delta),
        )
    labels = {
        "overdue": "просрочено", "current": "актуально",
        "upcoming": "ещё не наступило",
    }
    with patch("planner.views.timezone.now", return_value=now):
        for status, label in labels.items():
            response = Client().get("/reminders/", {"status": status})
            entries = response.context["entries"]
            assert len(entries) == 1
            assert entries[0]["reminder"]["text"] == status
            assert entries[0]["status"]["label"] == label
        response = Client().get("/reminders/?before=2026-10-27")
        assert [
            e["reminder"]["text"] for e in response.context["entries"]
        ] == ["overdue"]


@override_settings(USE_TZ=False)
def test_naive_datetimes_are_supported():
    Reminder.objects.all().delete()
    now = datetime(2026, 10, 27, 12, 0, 30)
    Reminder.objects.create(text="Сейчас", category_id=1, remind_at=now)
    with patch("planner.views.timezone.now", return_value=now):
        response = Client().get("/reminders/?status=current")
    assert response.status_code == 200
    assert response.context["entries"][0]["status"]["label"] == "актуально"


def test_edit_form_local_time_and_reminder_relation_validation():
    html = Client().get("/times/1/edit/").content.decode()
    assert 'value="2026-09-25T14:30"' in html
    payload = {
        "text": "Совпадает", "category_id": 1,
        "remind_at": "2026-09-25T14:30", "user_id": 1,
        "task_id": 1, "time_id": 1,
    }
    assert ReminderForm(payload).is_valid()
    form = ReminderForm({**payload, "remind_at": "2026-09-25T14:31"})
    assert not form.is_valid()
    assert "time_id" in form.errors
    form = ReminderForm({**payload, "user_id": 2})
    assert not form.is_valid()
    assert "user_id" in form.errors


def test_statistics_keep_zero_groups_and_completion_counts():
    Category.objects.create(name="Без задач")
    User.objects.create(name="Без задач", email="empty@example.org")
    response = Client().get("/statistics/?min_tasks=2")
    ctx = response.context
    assert ctx["totals"] == {
        "total_tasks": 3, "completed_tasks": 1, "open_tasks": 2,
        "cancelled_tasks": 0,
    }
    assert ctx["reminder_count"] == 2
    by_category = {row.name: (row.task_count, row.done_count)
                   for row in ctx["by_category"]}
    assert by_category["Без задач"] == (0, 0)
    assert sum(row[0] for row in by_category.values()) == 3
    assert sum(row[1] for row in by_category.values()) == 1
    assert sum(row.reminder_count for row in ctx["by_reminder_category"]) == 2
    assert [(row.name, row.task_count) for row in ctx["busy_users"]] == [
        ("Анна", 2),
    ]
    home = Client().get("/").context["sections"]
    assert [section["count"] for section in home] == [2, 3, 4, 3, 2]


def test_database_error_during_save_renders_error_page():
    with patch("planner.crud_views.User.objects.create",
               side_effect=DatabaseError("Unavailable")):
        response = Client().post(
            "/users/new/", {"name": "Test", "email": "new@example.org"},
        )
    assert response.status_code == 500


def test_duplicate_email_keeps_form_and_existing_record():
    response = Client().post(
        "/users/new/", {"name": "Test", "email": "anna@example.com"},
    )
    assert response.status_code == 200
    assert "email" in response.context["form"].errors
    assert User.objects.count() == 2
