"""ПР11: GET-формы фильтрации, ошибки и пагинация."""

import re
from datetime import date, datetime, timedelta
from html import unescape
from unittest.mock import patch
from urllib.parse import parse_qs

import pytest
from django import forms
from django.test import Client
from django.utils import timezone

from planner.forms import ReminderFilterForm, TaskFilterForm
from planner.models import Category, Reminder, Task, User

pytestmark = pytest.mark.usefixtures("orm_db")


@pytest.mark.parametrize("form_class", [ReminderFilterForm, TaskFilterForm])
@pytest.mark.parametrize("params", [
    {}, {"category": "0", "user": "0"}, {"category": "", "user": ""},
])
def test_optional_filters_and_legacy_zero(form_class, params):
    form = form_class(params)
    assert isinstance(form, forms.Form)
    assert form.is_valid(), form.errors
    assert form.cleaned_data["category"] is None
    if form_class is TaskFilterForm:
        assert form.cleaned_data["user"] is None
    assert '<option value="0"' in str(form["category"])


@pytest.mark.parametrize("form_class,date_name", [
    (ReminderFilterForm, "before"), (TaskFilterForm, "day"),
])
def test_valid_filters_return_typed_values(form_class, date_name):
    form = form_class({
        "q": "  поиск  ", "category": "1", "user": "1",
        date_name: "2026-11-20", "status": "all", "sort": "category",
    })
    assert form.is_valid(), form.errors
    assert form.cleaned_data["q"] == "поиск"
    assert form.cleaned_data[date_name] == date(2026, 11, 20)
    assert form.cleaned_data["category"] == Category.objects.get(pk=1)
    if form_class is TaskFilterForm:
        assert form.cleaned_data["user"] == User.objects.get(pk=1)
    else:
        assert form.cleaned_data["sort"] == "category"


@pytest.mark.parametrize("url,field,value", [
    (url, field, value)
    for url, date_name in [("/reminders/", "before"), ("/tasks/", "day")]
    for field, value in [
        ("q", "я" * 101), (date_name, "2026-02-30"),
        (date_name, "2026-1-1"), ("category", "missing"),
        ("category", "999999"), ("category", "9" * 5000),
        ("status", "unknown"),
    ]
] + [("/reminders/", "sort", "unknown"),
     ("/tasks/", "user", "missing"),
     ("/tasks/", "user", "999999"),
     ("/tasks/", "user", "9" * 5000)])
def test_invalid_parameters_show_errors_and_keep_input(url, field, value):
    response = Client().get(url, {field: value})
    assert response.status_code == 200
    form = response.context["filter_form"]
    assert not form.is_valid()
    assert field in form.errors
    assert form[field].value() == value
    html = response.content.decode()
    assert value in html
    assert "text-danger" in html


def test_task_filters_combine_and_invalid_field_keeps_valid_filters():
    moment = timezone.make_aware(datetime(2026, 11, 20, 12))
    matching = Task.objects.create(
        title="Совместный поиск", user_id=1, category_id=1,
        status=Task.Status.ACTIVE,
    )
    Task.objects.create(
        title="Совместный поиск", user_id=2, category_id=1,
        status=Task.Status.COMPLETED,
    )
    for offset in (0, 1):
        Reminder.objects.create(
            text="Связанное", task=matching, category_id=1,
            remind_at=moment + timedelta(minutes=offset),
        )
    params = {"q": "Совместный", "user": "1", "category": "1",
              "status": "open", "day": "2026-11-20"}
    client = Client()
    response = client.get("/tasks/", params)
    assert [e["task"].pk for e in response.context["entries"]] == [matching.pk]
    invalid = client.get("/tasks/", {**params, "day": "wrong"})
    assert [e["task"].pk for e in invalid.context["entries"]] == [matching.pk]
    assert "day" in invalid.context["filter_form"].errors


@pytest.mark.parametrize("before", ["2026-11-20", "wrong"])
def test_reminder_combined_filters_sort_and_pagination_keep_raw_params(before):
    moment = timezone.make_aware(datetime(2026, 11, 20, 12))
    category = Category.objects.create(name="Выборка & поиск")
    records = [Reminder.objects.create(
        text=f"Запись {i}", category=category,
        remind_at=moment + timedelta(minutes=i),
    ) for i in range(7)]
    Reminder.objects.create(
        text="Не подходит", category_id=1, remind_at=moment,
    )
    params = {"q": category.name, "category": str(category.pk),
              "before": before, "status": "upcoming", "sort": "-date"}
    with patch("planner.views._now", return_value=moment - timedelta(days=1)):
        first = Client().get("/reminders/", params)
        href = re.search(r'href="(\?[^\"]*page=2)"',
                         first.content.decode()).group(1)
        assert parse_qs(unescape(href)[1:]) == {
            **{key: [value] for key, value in params.items()}, "page": ["2"],
        }
        second = Client().get("/reminders/" + unescape(href))
    assert first.context["page_obj"].paginator.count == 7
    entries = first.context["entries"] + second.context["entries"]
    assert [e["reminder"]["id"] for e in entries] == [
        record.pk for record in reversed(records)
    ]
    assert second.context["filter_form"]["before"].value() == before
    assert "page" not in parse_qs(second.context["page_query"])
