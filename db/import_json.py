"""Перенос JSON ПР1–ПР6 в SQLite: python -m db.import_json.

Повторный импорт синхронизирует таблицы с JSON, поэтому изменения в SQLite
нужно делать после импорта, а не запускать импорт перед каждым GET.
"""

from db.database import get_connection
from db.init_db import init_database
from project_data import load_project_data


def import_json(db_path=None):
    """Перенести валидированные объекты в пять связанных таблиц атомарно."""
    data = load_project_data()
    category_ids = {item.name: item.id for item in data.categories}
    init_database(db_path)
    conn = get_connection(db_path)
    try:
        # Сначала удаляем дочерние записи, чтобы соблюсти FOREIGN KEY.
        for table in ("reminders", "tasks", "times", "categories", "users"):
            conn.execute(f"DELETE FROM {table}")
        conn.executemany(
            "INSERT INTO users (id, name, email) VALUES (?, ?, ?)",
            [(x.id, x.name, x.email) for x in data.users],
        )
        conn.executemany(
            "INSERT INTO categories (id, name, description) VALUES (?, ?, ?)",
            [(x.id, x.name, x.description) for x in data.categories],
        )
        conn.executemany(
            "INSERT INTO times (id, label, moment) VALUES (?, ?, ?)",
            [(x.id, x.label, x.moment.isoformat(timespec="minutes"))
             for x in data.times],
        )
        conn.executemany(
            """INSERT INTO tasks (
                   id, title, description, user_id, category_id, is_completed
               ) VALUES (?, ?, ?, ?, ?, ?)""",
            [(x.id, x.title, x.description, x.user_id, x.category_id,
              int(x.is_completed)) for x in data.tasks],
        )
        conn.executemany(
            """INSERT INTO reminders (
                   id, text, category_id, remind_at, user_id, task_id, time_id
               ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
            [(x.id, x.text, category_ids[x.category],
              x.remind_at.isoformat(timespec="minutes"),
              x.user_id, x.task_id, x.time_id) for x in data.reminders],
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    import_json()
    print("Данные из JSON импортированы в SQLite.")
