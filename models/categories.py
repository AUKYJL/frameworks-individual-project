"""Справочник категорий задач и напоминаний."""

from dataclasses import dataclass

from reminders import VALID_CATEGORIES
from .common import check_id, check_text


@dataclass
class Category:
    id: int
    name: str
    description: str = ""

    def __post_init__(self) -> None:
        check_id(self.id, "ID категории")
        check_text(self.name, "Название категории")
        if self.name not in VALID_CATEGORIES:
            raise ValueError("Неизвестная категория.")
        if not isinstance(self.description, str):
            raise ValueError("Описание категории должно быть строкой.")

    def __str__(self) -> str:
        return self.name

    def to_dict(self) -> dict:
        return {
            "id": self.id, "name": self.name,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Category":
        return cls(data["id"], data["name"], data.get("description", ""))
