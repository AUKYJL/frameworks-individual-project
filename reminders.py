from datetime import datetime


Reminder = dict[str, int | str]
VALID_CATEGORIES = {"учёба", "работа", "личное"}
REMINDER_STATUSES = {"ещё не наступило", "актуально", "просрочено"}


def _parse_reminder_time(remind_at: str) -> datetime:
    """Преобразовать дату напоминания из ISO-строки с точностью до минут."""
    if not isinstance(remind_at, str):
        raise ValueError("Дата напоминания должна быть строкой ISO 8601.")

    try:
        parsed_time = datetime.strptime(remind_at, "%Y-%m-%dT%H:%M")
    except ValueError as error:
        raise ValueError(
            "Дата напоминания должна иметь формат ГГГГ-ММ-ДДTЧЧ:ММ."
        ) from error
    return parsed_time


def _validate_reminder(reminder: Reminder) -> None:
    """Проверить структуру одной записи напоминания."""
    reminder_id = reminder.get("id")
    if (
        isinstance(reminder_id, bool)
        or not isinstance(reminder_id, int)
        or reminder_id <= 0
    ):
        raise ValueError(
            "ID напоминания должен быть положительным целым числом."
        )
    if (
        not isinstance(reminder.get("text"), str)
        or not reminder["text"].strip()
    ):
        raise ValueError("Текст напоминания не должен быть пустым.")
    if reminder.get("category") not in VALID_CATEGORIES:
        raise ValueError("Некорректная категория напоминания.")
    _parse_reminder_time(str(reminder.get("remind_at", "")))


def _validate_current_time(current_time: datetime) -> None:
    """Проверить переданное текущее время."""
    if not isinstance(current_time, datetime):
        raise ValueError("Текущее время должно быть объектом datetime.")


def get_reminder_status(
    reminder_time: datetime, current_time: datetime
) -> str:
    """Вернуть статус напоминания при сравнении времени до минуты."""
    reminder_minute = reminder_time.replace(second=0, microsecond=0)
    current_minute = current_time.replace(second=0, microsecond=0)

    if current_minute < reminder_minute:
        return "ещё не наступило"
    if current_minute == reminder_minute:
        return "актуально"
    return "просрочено"


def add_reminder(
    reminders: list[Reminder],
    text: str,
    category: str,
    remind_at: str,
) -> Reminder:
    """Проверить данные, добавить напоминание и вернуть созданную запись."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Текст напоминания не должен быть пустым.")
    if category not in VALID_CATEGORIES:
        raise ValueError("Некорректная категория напоминания.")
    _parse_reminder_time(remind_at)

    existing_ids: list[int] = []
    for reminder in reminders:
        _validate_reminder(reminder)
        existing_ids.append(int(reminder["id"]))

    reminder_id = max(existing_ids) + 1 if existing_ids else 1
    reminder: Reminder = {
        "id": reminder_id,
        "text": text.strip(),
        "category": category,
        "remind_at": remind_at,
    }
    reminders.append(reminder)
    return reminder


def cancel_reminder(reminders: list[Reminder], reminder_id: int) -> bool:
    """Удалить напоминание по ID и вернуть признак успешной отмены."""
    if (
        isinstance(reminder_id, bool)
        or not isinstance(reminder_id, int)
        or reminder_id <= 0
    ):
        raise ValueError(
            "ID напоминания должен быть положительным целым числом."
        )

    for index, reminder in enumerate(reminders):
        if reminder.get("id") == reminder_id:
            del reminders[index]
            return True
    return False


def find_reminders(reminders: list[Reminder], query: str) -> list[Reminder]:
    """Вернуть напоминания с текстом, содержащим запрос без учёта регистра."""
    if not isinstance(query, str) or not query.strip():
        raise ValueError("Поисковый запрос не должен быть пустым.")

    normalized_query = query.casefold()
    return [
        reminder
        for reminder in reminders
        if normalized_query in str(reminder.get("text", "")).casefold()
    ]


def filter_reminders_by_category(
    reminders: list[Reminder], category: str
) -> list[Reminder]:
    """Вернуть напоминания указанной категории."""
    if category not in VALID_CATEGORIES:
        raise ValueError("Некорректная категория напоминания.")
    return [
        reminder
        for reminder in reminders
        if reminder.get("category") == category
    ]


def filter_reminders_by_status(
    reminders: list[Reminder], status: str, current_time: datetime
) -> list[Reminder]:
    """Вернуть напоминания с указанным статусом в переданный момент."""
    if status not in REMINDER_STATUSES:
        raise ValueError("Некорректный статус напоминания.")
    _validate_current_time(current_time)
    return [
        reminder
        for reminder in reminders
        if get_reminder_status(
            _parse_reminder_time(str(reminder.get("remind_at", ""))),
            current_time,
        ) == status
    ]


def sort_reminders(
    reminders: list[Reminder], descending: bool = False
) -> list[Reminder]:
    """Вернуть новую коллекцию, отсортированную по времени напоминания."""
    if not isinstance(descending, bool):
        raise ValueError("Параметр descending должен быть булевым значением.")
    return sorted(
        reminders,
        key=lambda reminder: _parse_reminder_time(
            str(reminder.get("remind_at", ""))
        ),
        reverse=descending,
    )


def get_reminder_statistics(
    reminders: list[Reminder], current_time: datetime
) -> dict[str, int | dict[str, int]]:
    """Вернуть число напоминаний и распределения по категориям и статусам."""
    _validate_current_time(current_time)
    by_category: dict[str, int] = {}
    by_status: dict[str, int] = {}

    for reminder in reminders:
        _validate_reminder(reminder)
        category = str(reminder["category"])
        status = get_reminder_status(
            _parse_reminder_time(str(reminder["remind_at"])), current_time
        )
        by_category[category] = by_category.get(category, 0) + 1
        by_status[status] = by_status.get(status, 0) + 1

    return {
        "total": len(reminders),
        "by_category": by_category,
        "by_status": by_status,
    }


def get_category_message(category: str) -> str:
    """Вернуть сообщение, соответствующее категории напоминания."""
    if category == "учёба":
        return "Не забудьте выполнить учебную задачу."
    if category == "работа":
        return "Не забудьте выполнить рабочую задачу."
    return "Не забудьте о личном деле."


def format_reminder(
    user_name: str,
    reminder_text: str,
    reminder_time: datetime,
) -> str:
    """Сформировать текст напоминания с полной датой и временем."""
    formatted_time = reminder_time.strftime("%d.%m.%Y %H:%M")
    return (
        f"{user_name}, напоминаем: {reminder_text}. "
        f"Время: {formatted_time}."
    )
