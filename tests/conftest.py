"""Изолированная Django test DB без дополнительного pytest-плагина."""

import os
from io import StringIO

import pytest

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "reminder_site.settings")


def pytest_configure():
    try:
        import django
    except ImportError:
        return
    django.setup()


@pytest.fixture(scope="session")
def orm_database():
    django = pytest.importorskip("django")
    django.setup()
    from django.test.utils import (
        setup_databases, setup_test_environment, teardown_databases,
        teardown_test_environment,
    )
    setup_test_environment()
    config = setup_databases(verbosity=0, interactive=False)
    yield
    teardown_databases(config, verbosity=0)
    teardown_test_environment()


@pytest.fixture
def orm_db(orm_database, tmp_path):
    from django.core.management import call_command
    from django.db import transaction
    from db.import_json import import_json

    source = tmp_path / "pr7.sqlite"
    import_json(source)
    with transaction.atomic():
        call_command("import_pr7", source=source, stdout=StringIO())
        yield source
        transaction.set_rollback(True)
