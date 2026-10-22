"""Проверки шаблонной архитектуры ПР6 (при установленном Django)."""

import os
from unittest.mock import patch

import pytest

django = pytest.importorskip("django")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "reminder_site.settings")
django.setup()

from django.contrib.staticfiles import finders  # noqa: E402
from django.template.loader import get_template  # noqa: E402
from django.test import Client  # noqa: E402
from django.urls import reverse  # noqa: E402

from project_data import load_project_data  # noqa: E402


@pytest.mark.parametrize("url,template", [
    ("/", "homepage/index.html"),
    ("/reminders/", "planner/reminder_list.html"),
    ("/reminders/1/", "planner/reminder_detail.html"),
    ("/tasks/", "planner/task_list.html"),
    ("/tasks/1/", "planner/task_detail.html"),
    ("/users/", "planner/user_list.html"),
    ("/users/1/", "planner/user_detail.html"),
    ("/categories/", "planner/category_list.html"),
    ("/categories/1/", "planner/category_detail.html"),
    ("/times/", "planner/time_list.html"),
    ("/times/1/", "planner/time_detail.html"),
])
def test_page_uses_correct_template(url, template):
    response = Client().get(url)
    assert response.status_code == 200
    assert get_template(template)
    assert "<!DOCTYPE html>" in response.content.decode("utf-8")
    assert "Reminderly" in response.content.decode("utf-8")


@pytest.mark.parametrize("path", [
    "base.html", "includes/navigation.html",
    "planner/includes/reminder_card.html",
    "planner/includes/task_card.html",
    "planner/includes/status_badge.html",
    "planner/includes/task_status.html",
])
def test_shared_templates_exist(path):
    assert get_template(path)


@pytest.mark.parametrize("path", [
    "homepage/css/style.css", "homepage/js/main.js", "homepage/img/logo.svg",
])
def test_static_files_found(path):
    assert finders.find(path)


def test_navigation_uses_named_routes():
    html = Client().get("/").content.decode("utf-8")
    assert reverse("homepage:index") == "/"
    for route in (
        "planner:reminder_list", "planner:task_list",
        "planner:user_list", "planner:category_list",
        "planner:time_list",
    ):
        assert f'href="{reverse(route)}"' in html


def test_templates_escape_text_from_json():
    data = load_project_data()
    data.reminders[0].text = "<script>alert(123)</script>"
    with patch("planner.views.load_project_data", return_value=data):
        html = Client().get("/reminders/").content.decode("utf-8")
    assert "&lt;script&gt;alert(123)&lt;/script&gt;" in html
    assert "<script>alert(123)</script>" not in html


def test_empty_list_uses_empty_tag():
    data = load_project_data()
    data.reminders.clear()
    with patch("planner.views.load_project_data", return_value=data):
        html = Client().get("/reminders/").content.decode("utf-8")
    assert "Напоминаний пока нет" in html


def test_bad_json_returns_500_page():
    with patch("homepage.views.load_project_data",
               side_effect=ValueError("плохой JSON")):
        response = Client(raise_request_exception=False).get("/")
    assert response.status_code == 500
    assert "Ошибка чтения данных" in response.content.decode("utf-8")
