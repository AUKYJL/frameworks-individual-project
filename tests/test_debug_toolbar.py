"""Локальная панель отладки и постоянное число SQL-запросов страниц."""

import os
import subprocess
import sys
import textwrap

import pytest
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from planner.models import Reminder


@pytest.mark.parametrize("debug", ["0", "1"])
def test_toolbar_is_local_and_debug_only(debug):
    # Отдельный процесс проверяет реальную загрузку settings/URL/middleware,
    # без отключения панели, которое применяется к основному pytest-процессу.
    script = textwrap.dedent('''
        import re
        import django
        from django.conf import settings
        settings.DATABASES["default"]["NAME"] = ":memory:"
        django.setup()
        from django.core.management import call_command
        from django.test import Client
        from django.urls import resolve, Resolver404
        call_command("migrate", verbosity=0)
        assert settings.DEBUG_TOOLBAR_ENABLED == settings.DEBUG
        assert ("debug_toolbar" in settings.INSTALLED_APPS) == settings.DEBUG
        middleware = "debug_toolbar.middleware.DebugToolbarMiddleware"
        assert (middleware in settings.MIDDLEWARE) == settings.DEBUG
        client = Client()
        for ip in ("127.0.0.1", "::1", "192.0.2.1"):
            response = client.get("/reminders/", REMOTE_ADDR=ip)
            assert response.status_code == 200
            visible = bool(settings.DEBUG and ip in settings.INTERNAL_IPS)
            html = response.content.decode()
            assert ('id="djDebug"' in html) == visible
            if visible:
                from debug_toolbar.toolbar import DebugToolbar
                request_id = re.search('data-request-id="([^"]+)"', html)[1]
                panel = DebugToolbar.fetch(request_id).get_panel_by_id(
                    "SQLPanel")
                assert len(panel.get_stats()["queries"]) == 3
        try:
            resolve("/__debug__/render_panel/")
        except Resolver404:
            assert not settings.DEBUG
        else:
            assert settings.DEBUG
            assert client.get("/__debug__/render_panel/",
                              REMOTE_ADDR="192.0.2.1").status_code == 404
    ''')
    result = subprocess.run(
        [sys.executable, "-c", script],
        env={**os.environ, "DJANGO_DEBUG": debug},
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.usefixtures("orm_db")
@pytest.mark.parametrize("size", [1, 5, 12])
def test_reminder_sql_budget_does_not_grow_with_rows(size):
    original = Reminder.objects.get(pk=1)
    Reminder.objects.all().delete()
    for index in range(size):
        Reminder.objects.create(
            text=f"SQL probe {index}", category_id=original.category_id,
            user_id=original.user_id, task_id=original.task_id,
            time_id=original.time_id, remind_at=original.remind_at,
        )
    client = Client()
    for params in ({}, {"page": "2"}, {
        "q": "SQL probe", "category": str(original.category_id),
        "before": str(timezone.localdate(original.remind_at)),
        "sort": "category",
    }):
        with CaptureQueriesContext(connection) as captured:
            response = client.get("/reminders/", params)
        assert response.status_code == 200
        # ModelChoiceField дополнительно проверяет выбранную категорию.
        assert len(captured) == (5 if "category" in params else 4)
        rows = response.context["entries"]
        assert len(rows) <= 5
        sql = [query["sql"] for query in captured]
        assert sum("COUNT(*)" in query for query in sql) == 2
        row_sql = next(query for query in sql if 'AS "category_name"' in query)
        assert 'JOIN "planner_category"' in row_sql
        assert 'JOIN "planner_user"' in row_sql
        assert "LIMIT" in row_sql
    reminder_id = Reminder.objects.first().pk
    with CaptureQueriesContext(connection) as captured:
        response = client.get(f"/reminders/{reminder_id}/")
    assert response.status_code == 200
    assert len(captured) == 2
    for table in ("category", "user", "task", "time"):
        assert f'JOIN "planner_{table}"' in captured[0]["sql"]
