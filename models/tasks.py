"""Задача пользователя, связанная с категорией."""

from dataclasses import dataclass

from .common import check_id, check_text


@dataclass
class Task:
    id: int
    title: str
    description: str
    user_id: int
    category_id: int
    is_completed: bool = False

    def __post_init__(self) -> None:
        check_id(self.id, "ID задачи")
        check_text(self.title, "Название задачи")
        if not isinstance(self.description, str):
            raise ValueError("Описание задачи должно быть строкой.")
        check_id(self.user_id, "ID пользователя")
        check_id(self.category_id, "ID категории")
        if not isinstance(self.is_completed, bool):
            raise ValueError("Статус выполнения должен быть bool.")
        self.title = self.title.strip()

    def __str__(self) -> str:
        return self.title

    def mark_completed(self) -> None:
        self.is_completed = True

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "user_id": self.user_id,
            "category_id": self.category_id,
            "is_completed": self.is_completed,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        return cls(
            data["id"], data["title"], data["description"],
            data["user_id"], data["category_id"],
            data.get("is_completed", False),
        )
