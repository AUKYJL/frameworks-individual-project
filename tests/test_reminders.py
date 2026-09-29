"""Тесты бизнес-логики напоминаний."""

from datetime import datetime

import pytest

from reminders import (
    Reminder, add_reminder, cancel_reminder, filter_reminders_by_category,
    filter_reminders_by_status, find_reminders, get_reminder_statistics,
    get_reminder_status, sort_reminders,
)


CURRENT_TIME = datetime(2026, 9, 22, 12, 0)


def make_reminders() -> list[Reminder]:
    return [
        Reminder(
            2, "Подготовить отчёт", "работа", datetime(2026, 9, 22, 11, 59)
        ),
        Reminder(5, "Позвонить преподавателю", "учёба", CURRENT_TIME),
        Reminder(7, "Купить продукты", "личное", datetime(2026, 9, 22, 12, 1)),
    ]


def test_reminder_constructor_and_methods() -> None:
    reminder = Reminder(1, "  Подготовить отчёт  ", "работа", CURRENT_TIME)
    assert reminder.id == 1
    assert reminder.text == "Подготовить отчёт"
    assert reminder.category == "работа"
    assert reminder.remind_at == CURRENT_TIME
    assert str(reminder) == (
        "ID: 1 | Подготовить отчёт | Категория: работа | "
        "Время: 22.09.2026 12:00"
    )
    assert reminder.get_status(CURRENT_TIME) == "актуально"
    assert reminder.matches_query("ОТЧЁТ") is True
    assert reminder.get_category_message() == (
        "Не забудьте выполнить рабочую задачу."
    )
    assert reminder.format_for("Анна") == (
        "Анна, напоминаем: Подготовить отчёт. Время: 22.09.2026 12:00."
    )


@pytest.mark.parametrize("reminder_id, text, category, remind_at", [
    (0, "Задача", "учёба", CURRENT_TIME),
    (1, " ", "учёба", CURRENT_TIME),
    (1, "Задача", "другое", CURRENT_TIME),
    (1, "Задача", "учёба", "2026-09-22T12:00"),
])
def test_reminder_constructor_rejects_invalid_values(
    reminder_id: int, text: str, category: str, remind_at: object
) -> None:
    with pytest.raises(ValueError):
        Reminder(  # type: ignore[arg-type]
            reminder_id, text, category, remind_at
        )


def test_reschedule_and_serialization() -> None:
    reminder = Reminder(1, "Задача", "учёба", CURRENT_TIME)
    reminder.reschedule(datetime(2026, 9, 24, 9, 30))
    assert reminder.remind_at == datetime(2026, 9, 24, 9, 30)
    assert reminder.to_dict()["remind_at"] == "2026-09-24T09:30"
    with pytest.raises(ValueError):
        reminder.reschedule("2026-09-24T09:30")  # type: ignore[arg-type]


def test_add_cancel_search_filter_and_sort() -> None:
    reminders = make_reminders()
    reminder = add_reminder(
        reminders, "  Запланировать встречу  ", "работа", "2026-09-24T09:30"
    )
    assert reminder.id == 8 and reminder.text == "Запланировать встречу"
    assert cancel_reminder(reminders, 5) is True
    assert [item.id for item in reminders] == [2, 7, 8]
    assert find_reminders(reminders, "продукты") == [reminders[1]]
    assert filter_reminders_by_category(reminders, "работа") == [
        reminders[0], reminders[2]
    ]
    assert [item.id for item in sort_reminders(reminders)] == [2, 7, 8]


def test_status_filters_and_statistics() -> None:
    reminders = make_reminders()
    assert get_reminder_status(CURRENT_TIME, CURRENT_TIME) == "актуально"
    assert filter_reminders_by_status(
        reminders, "актуально", CURRENT_TIME
    ) == [reminders[1]]
    assert get_reminder_statistics(reminders, CURRENT_TIME)["total"] == 3


@pytest.mark.parametrize("category, remind_at", [
    ("другое", "2026-09-24T09:30"), ("учёба", "2026-02-30T09:30"),
])
def test_add_reminder_rejects_invalid_category_or_date(
    category: str, remind_at: str
) -> None:
    with pytest.raises(ValueError):
        add_reminder([], "Задача", category, remind_at)
