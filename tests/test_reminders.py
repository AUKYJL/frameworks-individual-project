"""Тесты бизнес-логики напоминаний."""

from datetime import datetime

import pytest

from reminders import (
    add_reminder,
    cancel_reminder,
    filter_reminders_by_category,
    filter_reminders_by_status,
    find_reminders,
    get_reminder_statistics,
    get_reminder_status,
    sort_reminders,
)


CURRENT_TIME = datetime(2026, 9, 22, 12, 0)


def make_reminders() -> list[dict[str, int | str]]:
    """Возвращает неизменяемый корректный набор данных для тестов."""
    return [
        {
            "id": 2,
            "text": "Подготовить отчёт",
            "category": "работа",
            "remind_at": "2026-09-22T11:59",
        },
        {
            "id": 5,
            "text": "Позвонить преподавателю",
            "category": "учёба",
            "remind_at": "2026-09-22T12:00",
        },
        {
            "id": 7,
            "text": "Купить продукты",
            "category": "личное",
            "remind_at": "2026-09-22T12:01",
        },
    ]


def test_add_reminder_assigns_unique_next_id() -> None:
    """Добавляет напоминание с новым уникальным идентификатором."""
    reminders = make_reminders()

    reminder = add_reminder(
        reminders, "  Запланировать встречу  ", "работа", "2026-09-24T09:30"
    )

    assert reminder["id"] == 8
    assert reminder["text"] == "Запланировать встречу"
    assert reminders[-1] == reminder


def test_cancel_reminder_handles_existing_and_missing_id() -> None:
    """Удаляет напоминание и отклоняет неизвестный идентификатор."""
    reminders = make_reminders()

    assert cancel_reminder(reminders, 5) is True
    assert [reminder["id"] for reminder in reminders] == [2, 7]
    assert cancel_reminder(reminders, 99) is False


def test_reminder_statuses() -> None:
    """Определяет статусы будущего, актуального и просроченного напоминаний."""
    assert get_reminder_status(datetime(2026, 9, 22, 12, 1), CURRENT_TIME) == (
        "ещё не наступило"
    )
    assert (
        get_reminder_status(datetime(2026, 9, 22, 12, 0), CURRENT_TIME)
        == "актуально"
    )
    assert (
        get_reminder_status(datetime(2026, 9, 22, 11, 59), CURRENT_TIME)
        == "просрочено"
    )


def test_search_filter_and_sort() -> None:
    """Ищет, фильтрует и сортирует напоминания."""
    reminders = make_reminders()

    assert find_reminders(reminders, "ПРЕПОДАВ") == [reminders[1]]
    assert filter_reminders_by_category(reminders, "работа") == [reminders[0]]
    assert [item["id"] for item in sort_reminders(reminders)] == [2, 5, 7]
    assert [
        item["id"] for item in sort_reminders(reminders, descending=True)
    ] == [7, 5, 2]


def test_filter_by_status_and_statistics() -> None:
    """Фильтрует по статусу и формирует статистику напоминаний."""
    reminders = make_reminders()

    assert filter_reminders_by_status(
        reminders, "актуально", CURRENT_TIME
    ) == [reminders[1]]
    assert get_reminder_statistics(reminders, CURRENT_TIME) == {
        "total": 3,
        "by_category": {"работа": 1, "учёба": 1, "личное": 1},
        "by_status": {
            "просрочено": 1,
            "актуально": 1,
            "ещё не наступило": 1,
        },
    }


@pytest.mark.parametrize(
    ("category", "remind_at"),
    [("другое", "2026-09-24T09:30"), ("учёба", "2026-02-30T09:30")],
)
def test_add_reminder_rejects_invalid_category_or_date(
    category: str, remind_at: str
) -> None:
    """Отклоняет напоминание с недопустимой категорией или датой."""
    with pytest.raises(ValueError):
        add_reminder([], "Задача", category, remind_at)
