"""Главная страница: счётчики предметных ORM-моделей."""

from django.shortcuts import render
from django.views.decorators.http import require_GET

from planner.models import Category, Reminder, Task, Time, User
from planner.views import db_page


@require_GET
@db_page
def index(request):
    """Передаёт счётчики объектов главной странице, не собирая HTML."""
    counts = {
        "reminder_count": Reminder.objects.count(),
        "task_count": Task.objects.count(),
        "category_count": Category.objects.count(),
        "user_count": User.objects.count(),
        "time_count": Time.objects.count(),
    }

    sections = [
        {"name": "Напоминания", "count": counts["reminder_count"],
         "route": "planner:reminder_list", "hint": "События и сроки"},
        {"name": "Задачи", "count": counts["task_count"],
         "route": "planner:task_list", "hint": "Дела пользователей"},
        {"name": "Категории", "count": counts["category_count"],
         "route": "planner:category_list", "hint": "Справочник категорий"},
        {"name": "Пользователи", "count": counts["user_count"],
         "route": "planner:user_list", "hint": "Авторы задач"},
        {"name": "Время", "count": counts["time_count"],
         "route": "planner:time_list", "hint": "Плановые моменты"},
    ]
    return render(request, "homepage/index.html", {"sections": sections})


def page_not_found(request, exception):
    """Отдельная страница неизвестного URL при DEBUG=False."""
    return render(request, "errors/not_found.html", status=404)
