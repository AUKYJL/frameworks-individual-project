"""Тесты JSON-хранилища."""

import json
from datetime import datetime
from pathlib import Path

from reminders import Reminder
import storage


def valid_reminders() -> list[Reminder]:
    return [
        Reminder(
            1, "Подготовить отчёт", "работа", datetime(2026, 9, 24, 9, 30)
        )
    ]


def set_data_file(monkeypatch, path: Path) -> None:
    monkeypatch.setattr(storage, "DATA_FILE", path)


def test_save_and_load_reminders_as_json(tmp_path: Path, monkeypatch) -> None:
    data_file = tmp_path / "data" / "reminders.json"
    set_data_file(monkeypatch, data_file)
    reminders = valid_reminders()

    assert storage.save_reminders(reminders) is True
    assert json.loads(data_file.read_text(encoding="utf-8")) == [
        {
            "id": 1,
            "text": "Подготовить отчёт",
            "category": "работа",
            "remind_at": "2026-09-24T09:30",
        }
    ]
    loaded = storage.load_reminders()
    assert isinstance(loaded, list)
    assert loaded[0].to_dict() == reminders[0].to_dict()
    assert loaded[0].remind_at == datetime(2026, 9, 24, 9, 30)


def test_load_reminders_returns_empty_list_for_missing_file(
    tmp_path: Path, monkeypatch
) -> None:
    set_data_file(monkeypatch, tmp_path / "missing.json")
    assert storage.load_reminders() == []


def test_load_reminders_returns_none_for_invalid_json(
    tmp_path: Path, monkeypatch
) -> None:
    data_file = tmp_path / "broken.json"
    data_file.write_text("{ not json", encoding="utf-8")
    set_data_file(monkeypatch, data_file)
    assert storage.load_reminders() is None
