"""Загрузка и сохранение напоминаний в JSON-файле."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from reminders import VALID_CATEGORIES


PROJECT_DIR = Path(__file__).resolve().parent
DATA_FILE = PROJECT_DIR / "data" / "reminders.json"
Reminder = dict[str, int | str]


def _validate_reminders(data: Any) -> list[Reminder]:
    """Проверить формат коллекции, загруженной из JSON."""
    if not isinstance(data, list):
        raise ValueError("Корневое значение должно быть списком напоминаний.")

    reminder_ids: set[int] = set()
    for index, reminder in enumerate(data, start=1):
        if not isinstance(reminder, dict):
            raise ValueError(f"Напоминание №{index} должно быть словарём.")

        required_fields = {"id", "text", "category", "remind_at"}
        missing_fields = required_fields - reminder.keys()
        if missing_fields:
            fields = ", ".join(sorted(missing_fields))
            raise ValueError(
                f"В напоминании №{index} отсутствуют поля: {fields}."
            )

        reminder_id = reminder["id"]
        if (
            isinstance(reminder_id, bool)
            or not isinstance(reminder_id, int)
            or reminder_id <= 0
        ):
            raise ValueError(
                f"ID напоминания №{index} должен быть положительным "
                "целым числом."
            )
        if reminder_id in reminder_ids:
            raise ValueError(f"ID напоминания №{index} не уникален.")
        reminder_ids.add(reminder_id)

        text = reminder["text"]
        if not isinstance(text, str) or not text.strip():
            raise ValueError(
                f"Текст напоминания №{index} не должен быть пустым."
            )

        category = reminder["category"]
        if not isinstance(category, str) or category not in VALID_CATEGORIES:
            raise ValueError(f"Категория напоминания №{index} недопустима.")

        remind_at = reminder["remind_at"]
        if not isinstance(remind_at, str):
            raise ValueError(f"Дата напоминания №{index} должна быть строкой.")
        try:
            parsed_time = datetime.strptime(remind_at, "%Y-%m-%dT%H:%M")
        except ValueError as error:
            raise ValueError(
                f"Дата напоминания №{index} имеет некорректный формат "
                "или значение."
            ) from error
        if parsed_time.strftime("%Y-%m-%dT%H:%M") != remind_at:
            raise ValueError(
                f"Дата напоминания №{index} должна иметь формат "
                "ГГГГ-ММ-ДДTЧЧ:ММ."
            )

    return data


def load_reminders() -> list[Reminder] | None:
    """Загрузить напоминания; вернуть ``None``, если файл нельзя использовать.

    При первом запуске, когда файла ещё нет, возвращается пустой список. Для
    повреждённого файла возвращается ``None``: это не позволяет случайно
    сохранить пустую коллекцию поверх пользовательских данных.
    """
    try:
        with DATA_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
        return _validate_reminders(data)
    except FileNotFoundError:
        return []
    except json.JSONDecodeError as error:
        print(
            f"Ошибка загрузки: файл {DATA_FILE} содержит некорректный JSON: "
            f"{error}."
        )
    except ValueError as error:
        print(f"Ошибка загрузки: некорректная структура данных: {error}")
    except OSError as error:
        print(f"Ошибка загрузки файла {DATA_FILE}: {error}")
    return None


def save_reminders(reminders: list[Reminder]) -> bool:
    """Проверить и сохранить напоминания; вернуть признак успеха."""
    try:
        _validate_reminders(reminders)
        DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
        with DATA_FILE.open("w", encoding="utf-8") as file:
            json.dump(reminders, file, ensure_ascii=False, indent=4)
        return True
    except ValueError as error:
        print(f"Ошибка сохранения: некорректные данные: {error}")
    except OSError as error:
        print(f"Ошибка сохранения файла {DATA_FILE}: {error}")
    return False
