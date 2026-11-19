"""Общие данные сервиса для шаблонов."""

from django.db import DatabaseError

from planner.models import Reminder


def service_context(request):
    try:
        count = Reminder.objects.count()
    except (DatabaseError, OSError):
        # Шаблон страницы ошибки должен работать и при недоступной БД.
        count = None
    return {"service_name": "Reminderly", "reminder_count": count}
