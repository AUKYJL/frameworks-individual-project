"""ПР11: ModelForm, даты, дубликаты и безопасная отмена задач."""

from datetime import timedelta
from unittest.mock import patch

import pytest
from django import forms
from django.core.exceptions import ValidationError
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from planner.forms import (
    CategoryForm, ReminderForm, TaskForm, TimeForm, UserForm,
)
from planner.models import Category, Reminder, Task, Time, User

pytestmark = pytest.mark.usefixtures("orm_db")


@pytest.fixture
def payload():
    return {
        "text": "Проверить почту", "category": 1, "user": 1,
        "remind_at": timezone.localtime(
            timezone.now() + timedelta(days=2),
        ).replace(second=0, microsecond=0).isoformat(timespec="minutes"),
    }


@pytest.mark.parametrize("form_class,model,fields", [
    (UserForm, User, ("name", "email")),
    (CategoryForm, Category, ("name", "description", "image")),
    (TimeForm, Time, ("label", "moment")),
    (TaskForm, Task, ("title", "description", "user", "category", "status")),
    (ReminderForm, Reminder,
     ("text", "category", "remind_at", "user", "task", "time")),
])
def test_model_forms_explicit_fields_and_widgets(form_class, model, fields):
    form = form_class()
    assert isinstance(form, forms.ModelForm)
    assert form._meta.model is model
    assert tuple(form._meta.fields) == fields
    assert tuple(form.fields) == fields
    for field in form.fields.values():
        expected = (
            "form-select" if isinstance(field.widget, forms.Select)
            else "form-control"
        )
        assert field.widget.attrs["class"] == expected


@pytest.mark.parametrize("form_class,field,limit", [
    (UserForm, "name", 120), (UserForm, "email", 254),
    (CategoryForm, "name", 100), (CategoryForm, "description", 500),
    (TimeForm, "label", 120), (TaskForm, "title", 200),
    (TaskForm, "description", 2000), (ReminderForm, "text", 500),
])
def test_length_limits(form_class, field, limit):
    form = form_class({field: "x" * (limit + 1)})
    assert not form.is_valid()
    errors = form.errors.as_data()[field]
    assert "max_length" in [error.code for error in errors]


def test_unique_validation_and_unchanged_instance():
    user = User.objects.get(pk=1)
    data = {"name": user.name, "email": user.email}
    assert "email" in UserForm(data).errors
    assert UserForm(data, instance=user).is_valid()
    category = Category.objects.get(pk=1)
    data = {"name": category.name, "description": category.description}
    assert "name" in CategoryForm(data).errors
    assert CategoryForm(data, instance=category).is_valid()


@pytest.mark.parametrize("text", ["... !!!", "💡", "   "])
def test_text_validator(payload, text):
    form = ReminderForm({**payload, "text": text})
    assert not form.is_valid()
    assert "text" in form.errors
    if text.strip():
        assert form.errors.as_data()["text"][0].code == "invalid_reminder_text"


def test_date_initial_and_explicit_initial(payload):
    before = timezone.now()
    form = ReminderForm()
    assert form.initial["remind_at"] > before
    assert form.fields["remind_at"].widget.input_type == "datetime-local"
    explicit = before + timedelta(days=3)
    form = ReminderForm(initial={"remind_at": explicit})
    assert form.initial["remind_at"] == explicit
    assert ReminderForm(payload).is_valid()


def test_past_dates_and_historical_edit(payload):
    past = timezone.now().replace(microsecond=0) - timedelta(days=2)
    past_data = {**payload, "remind_at": past.isoformat()}
    form = ReminderForm(past_data)
    assert not form.is_valid() and "remind_at" in form.errors
    reminder = Reminder.objects.create(
        text=payload["text"], category_id=1, user_id=1, remind_at=past,
    )
    form = ReminderForm(
        {**past_data, "text": "Обновлённый текст"}, instance=reminder,
    )
    assert form.is_valid(), form.errors
    form.save()
    reminder.refresh_from_db()
    assert reminder.remind_at == past
    assert reminder.text == "Обновлённый текст"
    assert ReminderForm(instance=reminder).initial["remind_at"] == past
    changed = ReminderForm(
        {**past_data, "remind_at": (past + timedelta(hours=1)).isoformat()},
        instance=reminder,
    )
    assert not changed.is_valid() and "remind_at" in changed.errors
    future = ReminderForm(payload, instance=reminder)
    assert future.is_valid(), future.errors


def test_duplicate_and_edit_exclusion(payload):
    form = ReminderForm(payload)
    assert form.is_valid(), form.errors
    reminder = form.save()
    duplicate = ReminderForm(payload)
    assert not duplicate.is_valid()
    assert "__all__" in duplicate.errors
    assert ReminderForm(payload, instance=reminder).is_valid()
    other_form = ReminderForm({**payload, "text": "Другое напоминание"})
    assert other_form.is_valid(), other_form.errors
    other = other_form.save()
    collision = ReminderForm(payload, instance=other)
    assert not collision.is_valid() and "__all__" in collision.errors
    for changed in ({"text": "Ещё текст"}, {"category": 2}, {"user": 2},
                    {"user": ""},
                    {"remind_at": timezone.now() + timedelta(days=3)}):
        form = ReminderForm({**payload, **changed})
        assert form.is_valid(), form.errors


@pytest.mark.parametrize("status,valid", [
    (Task.Status.ACTIVE, False), (Task.Status.CANCELLED, True),
    (Task.Status.COMPLETED, True),
])
def test_conflicts_ignore_finished_tasks(payload, status, valid):
    Task.objects.filter(pk=1).update(status=status)
    form = ReminderForm({**payload, "task": 1})
    assert form.is_valid(), form.errors
    form.save()
    candidate = ReminderForm(payload)
    assert candidate.is_valid() is valid


def test_null_user_duplicates(payload):
    data = {**payload, "user": ""}
    form = ReminderForm(data)
    assert form.is_valid(), form.errors
    form.save()
    assert "__all__" in ReminderForm(data).errors


@pytest.mark.parametrize("data", [{}, {"task": 1}, {"time": 1}, {
    "category": "missing", "user": 999999, "task": 1,
    "remind_at": "invalid", "text": "Текст",
}])
def test_incomplete_form_shows_errors(data):
    form = ReminderForm(data)
    assert not form.is_valid()
    assert form.errors


def test_incomplete_model_validation_is_validation_error():
    with pytest.raises(ValidationError) as error:
        Reminder(task_id=1).full_clean()
    assert "category" in error.value.message_dict


def test_cancel_route_and_button():
    client = Client()
    task = Task.objects.get(pk=1)
    reminder_ids = list(task.reminders.values_list("pk", flat=True))
    url = reverse("planner:task_cancel", args=[task.pk])
    html = client.get(f"/tasks/{task.pk}/").content.decode()
    assert f'action="{url}"' in html
    assert 'name="csrfmiddlewaretoken"' in html
    assert client.get(url).status_code == 405
    task.refresh_from_db()
    assert task.status == Task.Status.ACTIVE
    assert Client(enforce_csrf_checks=True).post(url).status_code == 403
    assert client.post(url).status_code == 302
    task.refresh_from_db()
    assert task.status == Task.Status.CANCELLED
    assert not task.is_completed
    assert list(task.reminders.values_list("pk", flat=True)) == reminder_ids
    html = client.get(f"/tasks/{task.pk}/").content.decode()
    assert f'action="{url}"' not in html
    assert client.post(url).status_code == 302
    missing_url = reverse("planner:task_cancel", args=[999999])
    assert client.post(missing_url).status_code == 404


@pytest.mark.parametrize("status", Task.Status.values)
def test_cancel_model_preserves_finished_status(status):
    task = Task.objects.get(pk=1)
    task.status = status
    task.save(update_fields=["status"])
    task.cancel()
    task.refresh_from_db()
    expected = (
        Task.Status.CANCELLED if status == Task.Status.ACTIVE else status
    )
    assert task.status == expected


def test_get_create_and_edit_never_save():
    client = Client()
    with patch("planner.forms.ReminderForm.save") as save:
        assert client.get("/reminders/new/").status_code == 200
        assert client.get("/reminders/1/edit/").status_code == 200
    save.assert_not_called()


@pytest.mark.parametrize("second,microsecond", [(42, 0), (0, 123456)])
def test_historical_date_widget_round_trip(payload, second, microsecond):
    past = (timezone.now() - timedelta(days=3)).replace(
        second=second, microsecond=microsecond,
    )
    reminder = Reminder.objects.create(
        text=payload["text"], category_id=1, user_id=1, remind_at=past,
    )
    form = ReminderForm(instance=reminder)
    field = form["remind_at"]
    displayed_date = field.field.widget.format_value(field.value())
    response = Client().post(f"/reminders/{reminder.pk}/edit/", {
        **payload, "remind_at": displayed_date,
    })
    assert response.status_code == 302
    reminder.refresh_from_db()
    assert reminder.remind_at == past


def test_duplicate_post_does_not_create_record(payload):
    client = Client()
    assert client.post("/reminders/new/", payload).status_code == 302
    count = Reminder.objects.count()
    response = client.post("/reminders/new/", payload)
    assert response.status_code == 200
    assert response.context["form"].non_field_errors()
    assert Reminder.objects.count() == count


def test_cancel_with_csrf_token():
    client = Client(enforce_csrf_checks=True)
    client.get("/tasks/1/")
    token = client.cookies["csrftoken"].value
    response = client.post(reverse("planner:task_cancel", args=[1]), {
        "csrfmiddlewaretoken": token,
    })
    assert response.status_code == 302
    assert Task.objects.get(pk=1).status == Task.Status.CANCELLED


def test_create_edit_cancel_and_reuse_same_time(payload):
    client = Client()
    task = Task.objects.create(
        title="Сценарий ПР11", user_id=1, category_id=1,
    )
    data = {**payload, "task": task.pk}
    response = client.post("/reminders/new/", data)
    assert response.status_code == 302
    reminder = Reminder.objects.get(task=task)
    target = f"/reminders/{reminder.pk}/edit/"
    assert client.post(target, data).status_code == 302
    response = client.post("/reminders/new/", payload)
    assert response.status_code == 200
    assert response.context["form"].non_field_errors()
    assert client.get("/reminders/999999/edit/").status_code == 404
    assert client.post(reverse(
        "planner:task_cancel", args=[task.pk],
    )).status_code == 302
    task.refresh_from_db()
    assert task.status == Task.Status.CANCELLED
    response = client.get("/tasks/", {"status": "open"})
    assert task.pk not in [entry["task"].pk for entry in
                           response.context["entries"]]
    assert client.post("/reminders/new/", payload).status_code == 302
    reminder.refresh_from_db()
    assert reminder.task_id == task.pk
