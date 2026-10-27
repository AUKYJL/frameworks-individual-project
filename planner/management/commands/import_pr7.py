"""python manage.py import_pr7 [--source data/reminderly.sqlite]."""

import sqlite3
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError, transaction
from django.utils import timezone

from planner.models import Category, Reminder, Task, Time, User


class Command(BaseCommand):
    help = "Перенести SQLite ПР7 в ORM без перезаписи существующих записей."

    def add_arguments(self, parser):
        parser.add_argument(
            "--source", type=Path,
            default=settings.BASE_DIR / "data" / "reminderly.sqlite",
        )

    def handle(self, *args, **options):
        source = Path(options["source"]).resolve()
        target = Path(settings.DATABASES["default"]["NAME"]).resolve()
        if source == target:
            raise CommandError("Исходная и целевая БД должны различаться.")
        counts = {}
        try:
            # mode=ro запрещает изменение и создание исходной БД.
            conn = sqlite3.connect(f"{source.as_uri()}?mode=ro", uri=True)
            conn.row_factory = sqlite3.Row
            try:
                conn.execute("BEGIN")  # Согласованный снимок пяти таблиц.
                with transaction.atomic():
                    for table, model in (
                        ("users", User), ("categories", Category),
                        ("times", Time), ("tasks", Task),
                        ("reminders", Reminder),
                    ):
                        created = unchanged = 0
                        for row in conn.execute(f"SELECT * FROM {table}"):
                            values = dict(row)
                            for field in ("moment", "remind_at"):
                                if field not in values:
                                    continue
                                moment = datetime.fromisoformat(values[field])
                                if (settings.USE_TZ
                                        and timezone.is_naive(moment)):
                                    moment = timezone.make_aware(
                                        moment,
                                        timezone.get_default_timezone(),
                                    )
                                elif not settings.USE_TZ and (
                                    timezone.is_aware(moment)
                                ):
                                    moment = timezone.make_naive(
                                        moment,
                                        timezone.get_default_timezone(),
                                    )
                                values[field] = moment
                            if "is_completed" in values:
                                if values["is_completed"] not in (0, 1):
                                    raise CommandError(
                                        "Некорректный статус задачи"
                                    )
                                values["is_completed"] = bool(
                                    values["is_completed"]
                                )
                            existing = model.objects.filter(
                                pk=values["id"],
                            ).first()
                            if existing is None:
                                model.objects.create(**values)
                                created += 1
                            elif all(
                                getattr(existing, key) == value
                                for key, value in values.items()
                            ):
                                unchanged += 1
                            else:
                                raise CommandError(
                                    f"Конфликт {table} id={values['id']}: "
                                    "значения различаются. Перенос отменён."
                                )
                        counts[table] = (created, unchanged)
            finally:
                conn.close()
        except (sqlite3.Error, DatabaseError, ValueError, OSError) as error:
            raise CommandError(f"Перенос отменён: {error}") from error
        for table, (created, unchanged) in counts.items():
            self.stdout.write(
                f"{table}: создано {created}, без изменений {unchanged}"
            )
