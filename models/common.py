"""Общие проверки классов предметной области (не Django ORM)."""


def check_id(value: int, name: str = "ID") -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} должен быть положительным целым числом.")


def check_text(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} не должен быть пустым.")
