"""Безопасный ввод данных для консольного приложения."""

from datetime import datetime

from reminders import VALID_CATEGORIES


def input_int(prompt: str = "Введите ID: ") -> int:
    """Запросить положительное целое число."""
    while True:
        value = input(prompt).strip()
        try:
            number = int(value)
        except ValueError:
            print("Введите положительное целое число.")
            continue
        if number <= 0:
            print("Введите положительное целое число.")
            continue
        return number


def input_non_empty_string(prompt: str = "Введите текст: ") -> str:
    """Запросить строку, содержащую хотя бы один непробельный символ."""
    while True:
        value = input(prompt).strip()
        if value:
            return value
        print("Значение не должно быть пустым.")


def input_category(prompt: str = "Введите категорию: ") -> str:
    """Запросить одну из допустимых категорий."""
    categories = ", ".join(sorted(VALID_CATEGORIES))
    while True:
        category = input(prompt).strip().casefold()
        if category in VALID_CATEGORIES:
            return category
        print(f"Неизвестная категория. Допустимые категории: {categories}.")


def input_datetime(
    prompt: str = "Введите дату и время (ДД.ММ.ГГГГ ЧЧ:ММ): ",
) -> datetime:
    """Запросить корректные дату и время в пользовательском формате."""
    while True:
        value = input(prompt).strip()
        try:
            parsed_time = datetime.strptime(value, "%d.%m.%Y %H:%M")
        except ValueError:
            print("Введите дату и время в формате ДД.ММ.ГГГГ ЧЧ:ММ.")
            continue
        if parsed_time.strftime("%d.%m.%Y %H:%M") != value:
            print("Введите дату и время в формате ДД.ММ.ГГГГ ЧЧ:ММ.")
            continue
        return parsed_time
