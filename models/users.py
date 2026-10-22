"""Пользователь сервиса напоминаний из ПР3 (не auth.User Django)."""

from dataclasses import dataclass

from .common import check_id, check_text


@dataclass
class User:
    id: int
    name: str
    email: str

    def __post_init__(self) -> None:
        check_id(self.id, "ID пользователя")
        check_text(self.name, "Имя пользователя")
        if (not isinstance(self.email, str) or "@" not in self.email
                or self.email.count("@") != 1 or " " in self.email):
            raise ValueError("Укажите корректную почту пользователя.")
        self.name = self.name.strip()
        self.email = self.email.strip()

    def __str__(self) -> str:
        return f"{self.name} ({self.email})"

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "email": self.email}

    @classmethod
    def from_dict(cls, data: dict) -> "User":
        return cls(data["id"], data["name"], data["email"])
