"""ПР7: данные из SQLite через sqlite3 и именованные SQL-запросы."""

import sqlite3
from datetime import datetime
from functools import wraps

from django.shortcuts import render
from django.views.decorators.http import require_GET

from db.database import fetch_all, fetch_one, fetch_record
from reminders import get_reminder_status


def db_page(func):
    """Показывать понятную страницу при недоступности БД."""
    @wraps(func)
    def wrapped(request, *args, **kwargs):
        try:
            return func(request, *args, **kwargs)
        except (sqlite3.Error, OSError, ValueError):
            return render(request, "errors/data_error.html", status=500)
    return wrapped


def _missing(request, entity_name):
    return render(
        request, "errors/not_found.html",
        {"entity_name": entity_name}, status=404,
    )


def _status(reminder, now):
    label = get_reminder_status(reminder["remind_at"], now)
    return {"label": label, "positive": label == "актуально"}


def _display_reminder(record):
    """Преобразовать ISO-время из sqlite3.Row для фильтра date в шаблоне."""
    item = dict(record)
    item["remind_at"] = datetime.fromisoformat(item["remind_at"])
    return item


def _reminder_entries(rows):
    now = datetime.now()
    return [
        {"reminder": record, "status": _status(record, now)}
        for record in map(_display_reminder, rows)
    ]


def _query(request):
    """Ограничить длину поискового выражения от пользователя."""
    return request.GET.get("q", "").strip()[:100]


def _selected_id(request, name):
    raw = request.GET.get(name, "0")
    return int(raw) if raw.isdecimal() and len(raw) <= 9 else 0


def _date_filter(request, name):
    """Проверить дату без исключений и SQL-конкатенации."""
    value = request.GET.get(name, "").strip()
    if not value:
        return "", ""
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d")
        if parsed.strftime("%Y-%m-%d") != value:
            raise ValueError("Неправильная дата")
    except ValueError:
        return "", "Укажите корректную дату в формате ГГГГ-ММ-ДД."
    return value, ""


@require_GET
@db_page
def reminders(request):
    query = _query(request)
    category_id = _selected_id(request, "category")
    before, date_error = _date_filter(request, "before")
    status = request.GET.get("status", "all")
    if status not in {"all", "upcoming", "current", "overdue"}:
        status = "all"
    now = datetime.now().isoformat(timespec="minutes")
    rows = fetch_all("search_reminders_filtered", (
        query, query, category_id, category_id,
        before, f"{before}T23:59:59" if before else "",
        status, now, now, status,
    ))
    return render(request, "planner/reminder_list.html", {
        "entries": _reminder_entries(rows),
        "categories": fetch_all("list_categories"),
        "query": query, "selected_category": category_id,
        "before": before, "date_error": date_error, "status": status,
        "filtered": bool(query or category_id or before or status != "all"),
    })


@require_GET
@db_page
def reminder_detail(request, reminder_id):
    row = fetch_one("reminder_detail", (reminder_id,))
    if row is None:
        return _missing(request, "Напоминание")
    reminder = _display_reminder(row)
    return render(request, "planner/reminder_detail.html", {
        "reminder": reminder,
        "category": {"id": row["category_id"], "name": row["category"]},
        "user": ({"id": row["user_id"], "name": row["user_name"]}
                 if row["user_id"] is not None else None),
        "task": ({"id": row["task_id"], "title": row["task_title"]}
                 if row["task_id"] is not None else None),
        "time": ({"id": row["time_id"], "label": row["time_label"]}
                 if row["time_id"] is not None else None),
        "status": _status(reminder, datetime.now()),
    })


@require_GET
@db_page
def users(request):
    query = _query(request)
    return render(request, "planner/user_list.html", {
        "users": fetch_all("search_users", (query, query, query)),
        "query": query,
    })


@require_GET
@db_page
def user_detail(request, user_id):
    user = fetch_record("users", user_id)
    if user is None:
        return _missing(request, "Пользователь")
    reminders_list = fetch_all("reminders_for_user", (user_id,))
    return render(request, "planner/user_detail.html", {
        "user": user,
        "tasks": fetch_all("tasks_for_user", (user_id,)),
        "reminders": reminders_list,
    })


@require_GET
@db_page
def categories(request):
    query = _query(request)
    return render(request, "planner/category_list.html", {
        "categories": fetch_all("search_categories", (query, query, query)),
        "query": query,
    })


@require_GET
@db_page
def category_detail(request, category_id):
    category = fetch_record("categories", category_id)
    if category is None:
        return _missing(request, "Категория")
    return render(request, "planner/category_detail.html", {
        "category": category,
        "tasks": fetch_all("tasks_for_category", (category_id,)),
        "reminders": fetch_all("reminders_for_category", (category_id,)),
    })


@require_GET
@db_page
def times(request):
    query = _query(request)
    day, date_error = _date_filter(request, "day")
    items = [dict(x) for x in fetch_all("search_times", (
        query, query, day, day,
    ))]
    for item in items:
        item["moment"] = datetime.fromisoformat(item["moment"])
    return render(request, "planner/time_list.html", {
        "times": items, "query": query,
        "day": day, "date_error": date_error,
    })


@require_GET
@db_page
def time_detail(request, time_id):
    row = fetch_record("times", time_id)
    if row is None:
        return _missing(request, "Время")
    time = dict(row)
    time["moment"] = datetime.fromisoformat(time["moment"])
    return render(request, "planner/time_detail.html", {
        "time": time,
        "reminders": fetch_all("reminders_for_time", (time_id,)),
    })


@require_GET
@db_page
def tasks(request):
    query = _query(request)
    requested_status = request.GET.get("status", "all")
    if requested_status not in ("all", "done", "open"):
        requested_status = "all"
    category_id = _selected_id(request, "category")
    rows = fetch_all("search_tasks", (
        query, query, query,
        requested_status, int(requested_status == "done"),
        category_id, category_id,
    ))
    entries = [
        {"task": row, "user": {"name": row["user_name"]},
         "category": {"name": row["category_name"]}}
        for row in rows
    ]
    return render(request, "planner/task_list.html", {
        "entries": entries, "status": requested_status,
        "query": query, "selected_category": category_id,
        "categories": fetch_all("list_categories"),
    })


@require_GET
@db_page
def task_detail(request, task_id):
    row = fetch_one("task_detail", (task_id,))
    if row is None:
        return _missing(request, "Задача")
    return render(request, "planner/task_detail.html", {
        "task": row,
        "user": {"id": row["user_id"], "name": row["user_name"]},
        "category": {"id": row["category_id"],
                     "name": row["category_name"]},
        "reminders": fetch_all("joined_reminders_for_task", (task_id,)),
    })


@require_GET
@db_page
def reminder_search(request):
    """Совместимость старого URL /search/ со списком /reminders/."""
    return reminders(request)


@require_GET
@db_page
def statistics(request):
    """SQL COUNT, SUM, GROUP BY и HAVING на реальных записях."""
    min_raw = request.GET.get("min_tasks", "1")
    min_tasks = int(min_raw) if min_raw.isdecimal() else 1
    min_tasks = max(1, min(min_tasks, 100))
    return render(request, "planner/statistics.html", {
        "totals": fetch_one("task_completion_totals"),
        "reminder_count": fetch_one("total_reminders")["count_reminders"],
        "by_category": fetch_all("tasks_by_category"),
        "by_user": fetch_all("tasks_by_user"),
        "by_reminder_category": fetch_all("reminders_by_category"),
        "busy_users": fetch_all("busy_users", (min_tasks,)),
        "min_tasks": min_tasks,
    })
