"""Офлайн-проверки структуры ПР6, не требующие установленного Django."""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.parametrize("relative", [
    "templates/base.html",
    "templates/includes/navigation.html",
    "templates/errors/not_found.html",
    "homepage/templates/homepage/index.html",
    "homepage/static/homepage/css/style.css",
    "homepage/static/homepage/js/main.js",
    "homepage/static/homepage/img/logo.svg",
    "planner/templates/planner/reminder_list.html",
    "planner/templates/planner/reminder_detail.html",
    "planner/templates/planner/task_list.html",
    "planner/templates/planner/task_detail.html",
    "planner/templates/planner/user_list.html",
    "planner/templates/planner/user_detail.html",
    "planner/templates/planner/category_list.html",
    "planner/templates/planner/category_detail.html",
    "planner/templates/planner/time_list.html",
    "planner/templates/planner/time_detail.html",
    "planner/templates/planner/includes/reminder_card.html",
    "planner/templates/planner/includes/task_card.html",
    "planner/templates/planner/includes/status_badge.html",
    "planner/templates/planner/includes/task_status.html",
])
def test_pr6_file_exists(relative):
    assert (ROOT / relative).is_file()


def test_base_template_contains_required_tags():
    base = (ROOT / "templates/base.html").read_text(encoding="utf-8")
    assert "{% load static %}" in base
    assert "{% block title %}" in base
    assert "{% block content %}" in base
    assert "{% include 'includes/navigation.html' %}" in base
    assert "{% static 'homepage/css/style.css' %}" in base
    assert "{% static 'homepage/js/main.js' %}" in base


def test_views_do_not_build_html_strings():
    for name in ("homepage", "planner"):
        source = (ROOT / name / "views.py").read_text(encoding="utf-8")
        assert "return render(" in source
        assert "HttpResponse(page(" not in source
        assert "<html" not in source
        assert "def page(" not in source


def test_all_pages_extend_base_template():
    paths = list((ROOT / "planner/templates/planner").glob("*.html"))
    paths += list((ROOT / "homepage/templates/homepage").glob("*.html"))
    assert len(paths) == 11
    for path in paths:
        assert "{% extends 'base.html' %}" in path.read_text(
            encoding="utf-8"
        )


def test_project_uses_real_template_dirs():
    settings = (ROOT / "reminder_site/settings.py").read_text(
        encoding="utf-8"
    )
    assert '"DIRS": [BASE_DIR / "templates"]' in settings
    assert '"APP_DIRS": True' in settings


def test_all_navigation_targets_are_reversed_in_templates():
    nav = (ROOT / "templates/includes/navigation.html").read_text(
        encoding="utf-8"
    )
    assert "{% url 'homepage:index' %}" in nav
    for name in ("reminder", "task", "user", "category", "time"):
        assert f"{{% url 'planner:{name}_list' %}}" in nav
