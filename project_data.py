"""Загрузка связанных сущностей из JSON для Django-страниц.

Не использует ORM. В ПР5 JSON-файлы остаются источником данных.
"""

import json
from dataclasses import dataclass

from models import Category, Reminder, Task, Time, User
from storage import PROJECT_DIR, load_reminders


@dataclass
class ProjectData:
    users: list[User]
    reminders: list[Reminder]
    categories: list[Category]
    times: list[Time]
    tasks: list[Task]

    def by_id(self, items: list, item_id: int):
        return next((item for item in items if item.id == item_id), None)

    def category_for_reminder(self, reminder):
        return next(
            (item for item in self.categories
             if item.name == reminder.category), None
        )


def _load_entities(filename: str, model: type) -> list:
    file = PROJECT_DIR / "data" / filename
    try:
        data = json.loads(file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        message = f"Не удалось загрузить {filename}: {error}"
        raise ValueError(message) from error
    if not isinstance(data, list):
        raise ValueError(f"{filename}: ожидается список объектов.")
    try:
        items = [model.from_dict(item) for item in data]
    except (TypeError, KeyError, ValueError) as error:
        raise ValueError(f"{filename}: неверные данные: {error}") from error
    ids = [item.id for item in items]
    if len(ids) != len(set(ids)):
        raise ValueError(f"{filename}: повторяются идентификаторы.")
    return items


def load_project_data() -> ProjectData:
    """Загрузить все пять коллекций и проверить межобъектные ссылки."""
    reminders = load_reminders()
    if reminders is None:
        raise ValueError("Не удалось прочитать reminders.json.")
    data = ProjectData(
        users=_load_entities("users.json", User),
        reminders=reminders,
        categories=_load_entities("categories.json", Category),
        times=_load_entities("times.json", Time),
        tasks=_load_entities("tasks.json", Task),
    )
    users = {item.id for item in data.users}
    categories = {item.id for item in data.categories}
    times = {item.id: item for item in data.times}
    tasks = {item.id: item for item in data.tasks}
    names = {item.name for item in data.categories}
    for task in data.tasks:
        if task.user_id not in users or task.category_id not in categories:
            raise ValueError(f"Задача №{task.id}: неверная ссылка.")
    for reminder in data.reminders:
        if reminder.category not in names:
            raise ValueError(f"Напоминание №{reminder.id}: нет категории.")
        if reminder.user_id is not None and reminder.user_id not in users:
            raise ValueError(f"Напоминание №{reminder.id}: нет пользователя.")
        if reminder.task_id is not None:
            task = tasks.get(reminder.task_id)
            if task is None:
                raise ValueError(f"Напоминание №{reminder.id}: нет задачи.")
            category = data.by_id(data.categories, task.category_id)
            if category.name != reminder.category:
                raise ValueError("Категории задачи и напоминания не совпали.")
            if reminder.user_id is not None:
                if task.user_id != reminder.user_id:
                    raise ValueError(
                        "Пользователи задачи и напоминания разные."
                    )
        if reminder.time_id is not None:
            time = times.get(reminder.time_id)
            if time is None or time.moment != reminder.remind_at:
                raise ValueError("Время напоминания не совпадает с Time.")
    return data
