"""Консольный интерфейс сервиса напоминаний."""

from datetime import datetime

from reminders import (
    REMINDER_STATUSES,
    VALID_CATEGORIES,
    add_reminder,
    cancel_reminder,
    filter_reminders_by_category,
    filter_reminders_by_status,
    find_reminders,
    format_reminder,
    get_category_message,
    get_reminder_statistics,
    get_reminder_status,
    sort_reminders,
)
from storage import load_reminders, save_reminders
from utils import (
    input_category,
    input_datetime,
    input_int,
    input_non_empty_string,
)


MENU = """
=== Сервис напоминаний ===

1. Показать все напоминания
2. Добавить напоминание
3. Отменить напоминание
4. Найти напоминание по тексту
5. Фильтровать по категории
6. Отсортировать по дате
7. Показать напоминания по статусу
8. Показать статистику
9. Выход
"""


def show_reminders(reminders: list[dict[str, int | str]]) -> None:
    """Вывести список напоминаний с текущими статусами."""
    if not reminders:
        print("Список напоминаний пуст.")
        return

    current_time = datetime.now()
    for reminder in reminders:
        remind_at = datetime.strptime(
            str(reminder["remind_at"]), "%Y-%m-%dT%H:%M"
        )
        status = get_reminder_status(remind_at, current_time)
        formatted_reminder = format_reminder(
            "Пользователь", str(reminder["text"]), remind_at
        )
        category_message = get_category_message(str(reminder["category"]))
        print(
            f"ID: {reminder['id']} | {formatted_reminder} | "
            f"Категория: {reminder['category']} | "
            f"Статус: {status}\n{category_message}"
        )


def input_status() -> str:
    """Запросить один из допустимых статусов."""
    statuses = ", ".join(sorted(REMINDER_STATUSES))
    while True:
        status = input("Введите статус: ").strip().casefold()
        if status in REMINDER_STATUSES:
            return status
        print(f"Неизвестный статус. Допустимые статусы: {statuses}.")


def input_sort_order() -> bool:
    """Вернуть признак сортировки по убыванию."""
    while True:
        order = input("Порядок (1 — возрастание, 2 — убывание): ").strip()
        if order == "1":
            return False
        if order == "2":
            return True
        print("Введите 1 или 2.")


def add_reminder_action(reminders: list[dict[str, int | str]]) -> None:
    """Добавить напоминание и сохранить изменения."""
    text = input_non_empty_string("Введите текст: ")
    category = input_category("Введите категорию: ")
    remind_at = input_datetime().strftime("%Y-%m-%dT%H:%M")
    reminder = add_reminder(reminders, text, category, remind_at)
    if save_reminders(reminders):
        print(f"Напоминание с ID {reminder['id']} добавлено.")
    else:
        reminders.remove(reminder)
        print("Напоминание не добавлено: не удалось сохранить данные.")


def cancel_reminder_action(reminders: list[dict[str, int | str]]) -> None:
    """Отменить напоминание и сохранить изменения."""
    reminder_id = input_int()
    reminder = next(
        (item for item in reminders if item.get("id") == reminder_id), None
    )
    if reminder is None:
        print("Напоминание с таким ID не найдено.")
        return

    reminder_index = reminders.index(reminder)
    cancel_reminder(reminders, reminder_id)
    if save_reminders(reminders):
        print("Напоминание отменено.")
    else:
        reminders.insert(reminder_index, reminder)
        print("Напоминание не отменено: не удалось сохранить данные.")


def show_statistics(reminders: list[dict[str, int | str]]) -> None:
    """Вывести общую статистику по напоминаниям."""
    statistics = get_reminder_statistics(reminders, datetime.now())
    print(f"Всего напоминаний: {statistics['total']}")
    print("По категориям:")
    for category in sorted(VALID_CATEGORIES):
        print(f"  {category}: {statistics['by_category'].get(category, 0)}")
    print("По статусам:")
    for status in sorted(REMINDER_STATUSES):
        print(f"  {status}: {statistics['by_status'].get(status, 0)}")


def main() -> None:
    """Запустить интерактивный сервис напоминаний."""
    reminders = load_reminders()
    if reminders is None:
        print(
            "Работа программы остановлена: исправьте файл данных и запустите "
            "её снова."
        )
        return

    while True:
        print(MENU)
        choice = input("Выберите пункт меню: ").strip()

        if choice == "1":
            show_reminders(reminders)
        elif choice == "2":
            add_reminder_action(reminders)
        elif choice == "3":
            cancel_reminder_action(reminders)
        elif choice == "4":
            query = input_non_empty_string("Введите текст для поиска: ")
            show_reminders(find_reminders(reminders, query))
        elif choice == "5":
            category = input_category("Введите категорию: ")
            show_reminders(filter_reminders_by_category(reminders, category))
        elif choice == "6":
            show_reminders(sort_reminders(reminders, input_sort_order()))
        elif choice == "7":
            show_reminders(
                filter_reminders_by_status(
                    reminders, input_status(), datetime.now()
                )
            )
        elif choice == "8":
            show_statistics(reminders)
        elif choice == "9":
            print("Работа программы завершена.")
            return
        else:
            print("Некорректный пункт меню. Введите число от 1 до 9.")


if __name__ == "__main__":
    main()
