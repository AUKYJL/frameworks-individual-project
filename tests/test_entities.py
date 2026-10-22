"""ПР5: предметные классы, JSON и отношения между сущностями."""

import json
from datetime import datetime

import pytest

from models import Category, Task, Time, User
from project_data import load_project_data
from reminders import Reminder
import project_data
import storage


def test_all_five_entities_have_links_and_serialization():
    data = load_project_data()
    assert len(data.categories) == 3
    assert len(data.users) == 2
    assert len(data.times) == 2
    assert len(data.tasks) == 3
    assert len(data.reminders) == 2

    reminder = data.by_id(data.reminders, 1)
    user = data.by_id(data.users, reminder.user_id)
    task = data.by_id(data.tasks, reminder.task_id)
    time = data.by_id(data.times, reminder.time_id)
    assert user.name == "Анна"
    assert task.user_id == user.id
    assert task.category_id == data.category_for_reminder(reminder).id
    assert time.moment == reminder.remind_at
    assert Reminder(3, "Проверка", "учёба", time.moment).to_dict() == {
        "id": 3, "text": "Проверка", "category": "учёба",
        "remind_at": "2026-09-25T14:30",
    }


def test_entity_validation_and_completion():
    user = User(4, "Ирина", "irina@example.org")
    assert user.to_dict()["name"] == "Ирина"
    category = Category(1, "учёба")
    assert category.to_dict()["name"] == "учёба"
    slot = Time(1, "Занятие", datetime(2026, 10, 22, 13, 0))
    assert Time.from_dict(slot.to_dict()).moment == slot.moment
    task = Task(1, "Учиться", "Python", 4, 1)
    assert task.is_completed is False
    task.mark_completed()
    assert task.to_dict()["is_completed"] is True

    with pytest.raises(ValueError):
        User(0, "Пётр", "peter@example.org")
    with pytest.raises(ValueError):
        Category(1, "неизвестная")
    with pytest.raises(ValueError):
        Time(1, "Пустое время", "2026-01-01")
    with pytest.raises(ValueError):
        Task(1, "Задача", "", 42, 0)
    with pytest.raises(ValueError):
        Reminder(1, "Задача", "учёба", slot.moment, task_id=-1)


def test_json_rejects_broken_task_relation(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    for name in ("users", "categories", "times", "tasks"):
        original = project_data.PROJECT_DIR / "data" / f"{name}.json"
        contents = json.loads(original.read_text(encoding="utf-8"))
        if name == "tasks":
            contents[0]["user_id"] = 999
        (data_dir / f"{name}.json").write_text(
            json.dumps(contents, ensure_ascii=False), encoding="utf-8"
        )
    reminders_file = tmp_path / "data" / "reminders.json"
    reminders_file.write_text(
        storage.DATA_FILE.read_text(encoding="utf-8"), encoding="utf-8"
    )
    monkeypatch.setattr(project_data, "PROJECT_DIR", tmp_path)
    monkeypatch.setattr(storage, "DATA_FILE", reminders_file)
    with pytest.raises(ValueError, match="неверная ссылка"):
        load_project_data()


def test_reminder_legacy_and_linked_json(tmp_path, monkeypatch):
    path = tmp_path / "reminders.json"
    monkeypatch.setattr(storage, "DATA_FILE", path)
    old = Reminder(1, "Старое", "работа", datetime(2026, 12, 1, 14))
    new = Reminder(
        2, "Новое", "учёба", datetime(2026, 12, 2, 15),
        user_id=1, task_id=1, time_id=1,
    )
    assert storage.save_reminders([old, new]) is True
    result = storage.load_reminders()
    assert result is not None
    assert result[0].task_id is None
    assert result[1].task_id == 1
    assert result[1].to_dict() == new.to_dict()
