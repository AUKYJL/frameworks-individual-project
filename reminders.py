"""Бизнес-логика сервиса напоминаний."""

from datetime import datetime


VALID_CATEGORIES = {"учёба", "работа", "личное"}
REMINDER_STATUSES = {"ещё не наступило", "актуально", "просрочено"}


def _parse_reminder_time(remind_at: str) -> datetime:
    """Преобразовать дату из ISO-строки с точностью до минут."""
    if not isinstance(remind_at, str):
        raise ValueError("Дата напоминания должна быть строкой ISO 8601.")
    try:
        result = datetime.strptime(remind_at, "%Y-%m-%dT%H:%M")
    except ValueError as error:
        raise ValueError(
            "Дата напоминания должна иметь формат ГГГГ-ММ-ДДTЧЧ:ММ."
        ) from error
    if result.strftime("%Y-%m-%dT%H:%M") != remind_at:
        raise ValueError(
            "Дата напоминания должна иметь формат ГГГГ-ММ-ДДTЧЧ:ММ."
        )
    return result


def _validate_current_time(current_time: datetime) -> None:
    if not isinstance(current_time, datetime):
        raise ValueError("Текущее время должно быть объектом datetime.")


def get_reminder_status(
    reminder_time: datetime, current_time: datetime
) -> str:
    """Вернуть статус напоминания при сравнении времени до минуты."""
    _validate_current_time(reminder_time)
    _validate_current_time(current_time)
    reminder_minute = reminder_time.replace(second=0, microsecond=0)
    current_minute = current_time.replace(second=0, microsecond=0)
    if current_minute < reminder_minute:
        return "ещё не наступило"
    if current_minute == reminder_minute:
        return "актуально"
    return "просрочено"


def get_category_message(category: str) -> str:
    """Вернуть сообщение, соответствующее категории напоминания."""
    if category == "учёба":
        return "Не забудьте выполнить учебную задачу."
    if category == "работа":
        return "Не забудьте выполнить рабочую задачу."
    return "Не забудьте о личном деле."


def format_reminder(
    user_name: str, reminder_text: str, reminder_time: datetime
) -> str:
    """Сформировать текст напоминания с полной датой и временем."""
    return (
        f"{user_name}, напоминаем: {reminder_text}. Время: "
        f"{reminder_time.strftime('%d.%m.%Y %H:%M')}.")


class Reminder:
    """Напоминание с валидированными данными и поведением сущности."""

    def __init__(
        self, id: int, text: str, category: str, remind_at: datetime,
        *, user_id: int | None = None, task_id: int | None = None,
        time_id: int | None = None
    ) -> None:
        if (isinstance(id, bool) or not isinstance(id, int) or id <= 0):
            raise ValueError(
                "ID напоминания должен быть положительным целым числом."
            )
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Текст напоминания не должен быть пустым.")
        if not isinstance(category, str) or category not in VALID_CATEGORIES:
            raise ValueError("Некорректная категория напоминания.")
        if not isinstance(remind_at, datetime):
            raise ValueError("Дата напоминания должна быть объектом datetime.")
        self.id = id
        self.text = text.strip()
        self.category = category
        self.remind_at = remind_at
        for field, value in (
            ("user_id", user_id), ("task_id", task_id),
            ("time_id", time_id),
        ):
            if value is not None and (
                isinstance(value, bool) or not isinstance(value, int)
                or value <= 0
            ):
                raise ValueError(f"{field} должен быть положительным ID.")
        self.user_id = user_id
        self.task_id = task_id
        self.time_id = time_id

    def __str__(self) -> str:
        return (
            f"ID: {self.id} | {self.text} | Категория: {self.category} | "
            f"Время: {self.remind_at.strftime('%d.%m.%Y %H:%M')}"
        )

    def get_status(self, current_time: datetime) -> str:
        return get_reminder_status(self.remind_at, current_time)

    def matches_query(self, query: str) -> bool:
        if not isinstance(query, str) or not query.strip():
            raise ValueError("Поисковый запрос не должен быть пустым.")
        return query.casefold() in self.text.casefold()

    def reschedule(self, remind_at: datetime) -> None:
        if not isinstance(remind_at, datetime):
            raise ValueError("Дата напоминания должна быть объектом datetime.")
        self.remind_at = remind_at
        # Смена даты делает прежнюю ссылку на Time неактуальной.
        self.time_id = None

    def format_for(self, user_name: str) -> str:
        return format_reminder(user_name, self.text, self.remind_at)

    def get_category_message(self) -> str:
        return get_category_message(self.category)

    def to_dict(self) -> dict[str, int | str]:
        data = {
            "id": self.id,
            "text": self.text,
            "category": self.category,
            "remind_at": self.remind_at.strftime("%Y-%m-%dT%H:%M"),
        }
        # Старый JSON ПР3 не содержит ссылок. Сохраняем совместимость.
        for field in ("user_id", "task_id", "time_id"):
            value = getattr(self, field)
            if value is not None:
                data[field] = value
        return data


def _validate_reminder(reminder: Reminder) -> None:
    if not isinstance(reminder, Reminder):
        raise ValueError("Напоминание должно быть объектом Reminder.")


def add_reminder(
    reminders: list[Reminder], text: str, category: str, remind_at: str
) -> Reminder:
    """Создать объект, добавить его в коллекцию и вернуть его."""
    reminder_time = _parse_reminder_time(remind_at)
    for reminder in reminders:
        _validate_reminder(reminder)
    reminder_id = max((item.id for item in reminders), default=0) + 1
    reminder = Reminder(reminder_id, text, category, reminder_time)
    reminders.append(reminder)
    return reminder


def cancel_reminder(reminders: list[Reminder], reminder_id: int) -> bool:
    if (isinstance(reminder_id, bool) or not isinstance(reminder_id, int)
            or reminder_id <= 0):
        raise ValueError(
            "ID напоминания должен быть положительным целым числом."
        )
    for index, reminder in enumerate(reminders):
        _validate_reminder(reminder)
        if reminder.id == reminder_id:
            del reminders[index]
            return True
    return False


def find_reminders(reminders: list[Reminder], query: str) -> list[Reminder]:
    if not isinstance(query, str) or not query.strip():
        raise ValueError("Поисковый запрос не должен быть пустым.")
    return [
        reminder for reminder in reminders if reminder.matches_query(query)
    ]


def filter_reminders_by_category(
    reminders: list[Reminder], category: str
) -> list[Reminder]:
    if category not in VALID_CATEGORIES:
        raise ValueError("Некорректная категория напоминания.")
    return [
        reminder for reminder in reminders if reminder.category == category
    ]


def filter_reminders_by_status(
    reminders: list[Reminder], status: str, current_time: datetime
) -> list[Reminder]:
    if status not in REMINDER_STATUSES:
        raise ValueError("Некорректный статус напоминания.")
    _validate_current_time(current_time)
    return [
        item for item in reminders if item.get_status(current_time) == status
    ]


def sort_reminders(
    reminders: list[Reminder], descending: bool = False
) -> list[Reminder]:
    if not isinstance(descending, bool):
        raise ValueError("Параметр descending должен быть булевым значением.")
    return sorted(
        reminders, key=lambda item: item.remind_at, reverse=descending
    )


def get_reminder_statistics(
    reminders: list[Reminder], current_time: datetime
) -> dict[str, int | dict[str, int]]:
    _validate_current_time(current_time)
    by_category: dict[str, int] = {}
    by_status: dict[str, int] = {}
    for reminder in reminders:
        _validate_reminder(reminder)
        by_category[reminder.category] = (
            by_category.get(reminder.category, 0) + 1
        )
        status = reminder.get_status(current_time)
        by_status[status] = by_status.get(status, 0) + 1
    return {
        "total": len(reminders),
        "by_category": by_category,
        "by_status": by_status,
    }
