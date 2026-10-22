"""HTTP-представления: получение объектов из JSON и передача контекста."""

from datetime import datetime

from django.shortcuts import render
from django.views.decorators.http import require_GET

from project_data import load_project_data


def _read_data(request):
    """Возвращает данные или HTTP-ответ при повреждённом JSON."""
    try:
        return load_project_data(), None
    except ValueError:
        return None, render(request, "errors/data_error.html", status=500)


def _missing(request, entity_name):
    return render(
        request, "errors/not_found.html",
        {"entity_name": entity_name}, status=404,
    )


def _status(reminder, now):
    status = reminder.get_status(now)
    return {"label": status, "positive": status == "актуально"}


@require_GET
def reminders(request):
    data, error = _read_data(request)
    if error is not None:
        return error
    now = datetime.now()
    entries = [
        {"reminder": reminder, "status": _status(reminder, now)}
        for reminder in sorted(data.reminders, key=lambda r: r.remind_at)
    ]
    return render(request, "planner/reminder_list.html", {"entries": entries})


@require_GET
def reminder_detail(request, reminder_id):
    data, error = _read_data(request)
    if error is not None:
        return error
    reminder = data.by_id(data.reminders, reminder_id)
    if reminder is None:
        return _missing(request, "Напоминание")
    return render(request, "planner/reminder_detail.html", {
        "reminder": reminder,
        "category": data.category_for_reminder(reminder),
        "user": data.by_id(data.users, reminder.user_id),
        "task": data.by_id(data.tasks, reminder.task_id),
        "time": data.by_id(data.times, reminder.time_id),
        "status": _status(reminder, datetime.now()),
    })


@require_GET
def users(request):
    data, error = _read_data(request)
    if error is not None:
        return error
    return render(request, "planner/user_list.html", {"users": data.users})


@require_GET
def user_detail(request, user_id):
    data, error = _read_data(request)
    if error is not None:
        return error
    user = data.by_id(data.users, user_id)
    if user is None:
        return _missing(request, "Пользователь")
    return render(request, "planner/user_detail.html", {
        "user": user,
        "tasks": [t for t in data.tasks if t.user_id == user.id],
        "reminders": [r for r in data.reminders if r.user_id == user.id],
    })


@require_GET
def categories(request):
    data, error = _read_data(request)
    if error is not None:
        return error
    return render(request, "planner/category_list.html", {
        "categories": data.categories,
    })


@require_GET
def category_detail(request, category_id):
    data, error = _read_data(request)
    if error is not None:
        return error
    category = data.by_id(data.categories, category_id)
    if category is None:
        return _missing(request, "Категория")
    return render(request, "planner/category_detail.html", {
        "category": category,
        "tasks": [t for t in data.tasks if t.category_id == category.id],
        "reminders": [
            r for r in data.reminders if r.category == category.name
        ],
    })


@require_GET
def times(request):
    data, error = _read_data(request)
    if error is not None:
        return error
    return render(request, "planner/time_list.html", {"times": data.times})


@require_GET
def time_detail(request, time_id):
    data, error = _read_data(request)
    if error is not None:
        return error
    item = data.by_id(data.times, time_id)
    if item is None:
        return _missing(request, "Время")
    return render(request, "planner/time_detail.html", {
        "time": item,
        "reminders": [r for r in data.reminders if r.time_id == item.id],
    })


@require_GET
def tasks(request):
    data, error = _read_data(request)
    if error is not None:
        return error
    entries = [
        {
            "task": task,
            "user": data.by_id(data.users, task.user_id),
            "category": data.by_id(data.categories, task.category_id),
        }
        for task in data.tasks
    ]
    return render(request, "planner/task_list.html", {"entries": entries})


@require_GET
def task_detail(request, task_id):
    data, error = _read_data(request)
    if error is not None:
        return error
    task = data.by_id(data.tasks, task_id)
    if task is None:
        return _missing(request, "Задача")
    return render(request, "planner/task_detail.html", {
        "task": task,
        "user": data.by_id(data.users, task.user_id),
        "category": data.by_id(data.categories, task.category_id),
        "reminders": [r for r in data.reminders if r.task_id == task.id],
    })
