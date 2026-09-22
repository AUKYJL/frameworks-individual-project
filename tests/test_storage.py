"""Тесты JSON-хранилища."""

import json
from pathlib import Path

import storage


def valid_reminders() -> list[dict[str, int | str]]:
    """Возвращает минимальный корректный набор данных для JSON."""
    return [
        {
            "id": 1,
            "text": "Подготовить отчёт",
            "category": "работа",
            "remind_at": "2026-09-24T09:30",
        }
    ]


def set_data_file(monkeypatch, path: Path) -> None:
    """Перенаправляет модуль хранилища на тестовый файл."""
    monkeypatch.setattr(storage, "DATA_FILE", path)


def test_save_and_load_reminders_as_json(tmp_path: Path, monkeypatch) -> None:
    """Сохраняет напоминания в JSON и загружает их без изменений."""
    data_file = tmp_path / "data" / "reminders.json"
    set_data_file(monkeypatch, data_file)
    reminders = valid_reminders()

    assert storage.save_reminders(reminders) is True
    assert json.loads(data_file.read_text(encoding="utf-8")) == reminders
    assert storage.load_reminders() == reminders


def test_load_reminders_returns_empty_list_for_missing_file(
    tmp_path: Path, monkeypatch
) -> None:
    """Возвращает пустой список, если файл с напоминаниями отсутствует."""
    set_data_file(monkeypatch, tmp_path / "missing.json")

    assert storage.load_reminders() == []


def test_load_reminders_returns_none_for_invalid_json(
    tmp_path: Path, monkeypatch
) -> None:
    """Возвращает None, если файл содержит некорректный JSON."""
    data_file = tmp_path / "broken.json"
    data_file.write_text("{ not json", encoding="utf-8")
    set_data_file(monkeypatch, data_file)

    assert storage.load_reminders() is None
