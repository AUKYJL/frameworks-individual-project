"""Отдельная сущность времени: запланированные моменты уведомления."""

from dataclasses import dataclass
from datetime import datetime

from reminders import _parse_reminder_time
from .common import check_id, check_text


@dataclass
class Time:
    id: int
    label: str
    moment: datetime

    def __post_init__(self) -> None:
        check_id(self.id, "ID времени")
        check_text(self.label, "Название времени")
        if not isinstance(self.moment, datetime):
            raise ValueError("Момент времени должен быть datetime.")
        self.label = self.label.strip()

    def __str__(self) -> str:
        return f"{self.label}: {self.moment:%d.%m.%Y %H:%M}"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "moment": self.moment.strftime("%Y-%m-%dT%H:%M"),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Time":
        return cls(
            data["id"], data["label"],
            _parse_reminder_time(data["moment"]),
        )
