"""Главная страница и обработка 404 (ПР6: Django Templates)."""

from django.shortcuts import render
from django.views.decorators.http import require_GET

from project_data import load_project_data


@require_GET
def index(request):
    """Передаёт счётчики объектов главной странице, не собирая HTML."""
    try:
        data = load_project_data()
    except ValueError:
        return render(request, "errors/data_error.html", status=500)

    sections = [
        {"name": "Напоминания", "count": len(data.reminders),
         "route": "planner:reminder_list", "hint": "События и сроки"},
        {"name": "Задачи", "count": len(data.tasks),
         "route": "planner:task_list", "hint": "Дела пользователей"},
        {"name": "Категории", "count": len(data.categories),
         "route": "planner:category_list", "hint": "Справочник категорий"},
        {"name": "Пользователи", "count": len(data.users),
         "route": "planner:user_list", "hint": "Авторы задач"},
        {"name": "Время", "count": len(data.times),
         "route": "planner:time_list", "hint": "Плановые моменты"},
    ]
    return render(request, "homepage/index.html", {"sections": sections})


def page_not_found(request, exception):
    """Отдельная страница неизвестного URL при DEBUG=False."""
    return render(request, "errors/not_found.html", status=404)
