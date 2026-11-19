"""Admin: права доступа, CRUD, связанные поля и общая валидация."""

from datetime import timedelta

import pytest
from django.apps import apps
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.db import connection
from django.urls import reverse
from django.utils import timezone

from planner.models import Category, Reminder, Task, Time, User

pytestmark = pytest.mark.usefixtures("orm_db")
MODELS = (User, Category, Time, Task, Reminder)


@pytest.fixture
def admin_client():
    account = get_user_model().objects.create(
        username="admin-test",
        is_staff=True,
        is_superuser=True,
    )
    account.set_unusable_password()
    account.save()
    client = Client()
    client.force_login(account)
    return client


def url(model, action, *args):
    return reverse(f"admin:planner_{
            model._meta.model_name}_{action}", args=args)


def reminder_data(**overrides):
    reminder = Reminder.objects.get(pk=1)
    moment = timezone.localtime(reminder.remind_at)
    return {
        "text": "Проверка Admin",
        "category": reminder.category_id,
        "user": reminder.user_id or "",
        "task": reminder.task_id or "",
        "time": reminder.time_id or "",
        "remind_at_0": moment.strftime("%Y-%m-%d"),
        "remind_at_1": moment.strftime("%H:%M:%S"),
        **overrides,
    }


@pytest.mark.parametrize("model", MODELS)
def test_registration_pages_and_localization(admin_client, model):
    assert isinstance(admin.site._registry[model], admin.ModelAdmin)
    assert model._meta.verbose_name != model.__name__.lower()
    for field in model._meta.fields:
        if field.name != "id":
            assert str(field.verbose_name) != field.name.replace("_", " ")
    for action, args in [("changelist", ()), ("add", ()), ("change", (1,))]:
        assert admin_client.get(url(model, action, *args)).status_code == 200
    assert (
        apps.get_app_config("planner").verbose_name == "Планировщик Reminderly"
    )
    assert get_user_model() is not User
    index = admin_client.get(reverse("admin:index"))
    assert "Reminderly" in index.content.decode()


def test_access_requires_auth_staff_and_permissions(admin_client):
    target = url(Task, "changelist")
    assert Client().get(target).status_code == 302
    account = get_user_model().objects.create(username="ordinary")
    client = Client()
    client.force_login(account)
    assert client.get(target).status_code == 302
    account.is_staff = True
    account.save()
    assert client.get(target).status_code == 403
    assert admin_client.get(target).status_code == 200


@pytest.mark.parametrize(
    "model,lookup,query",
    [
        (Task, "user__email", "admin-search@example.org"),
        (Task, "category__name", "Уникальная категория Admin"),
        (Reminder, "task__title", "Уникальная задача Admin"),
        (Reminder, "user__email", "admin-search@example.org"),
        (Reminder, "time__label", "Уникальное время Admin"),
    ],
)
def test_related_search(admin_client, model, lookup, query):
    reminder = Reminder.objects.select_related("task", "user", "time").get(
        pk=1
    )
    task = reminder.task
    User.objects.filter(pk=task.user_id).update(
        email="admin-search@example.org"
    )
    Category.objects.filter(pk=task.category_id).update(
        name="Уникальная категория Admin",
    )
    Task.objects.filter(pk=task.pk).update(title="Уникальная задача Admin")
    Time.objects.filter(pk=reminder.time_id).update(
        label="Уникальное время Admin"
    )
    response = admin_client.get(url(model, "changelist"), {"q": query})
    expected = set(
        model.objects.filter(**{lookup: query}).values_list("pk", flat=True)
    )
    assert expected
    assert {row.pk for row in response.context["cl"].result_list} == expected


@pytest.mark.parametrize("model", (Task, Reminder))
def test_list_select_related_avoids_extra_queries(admin_client, model):
    response = admin_client.get(url(model, "changelist"))
    rows = list(response.context["cl"].result_list)
    with CaptureQueriesContext(connection) as queries:
        for row in rows:
            for field in admin.site._registry[model].list_select_related:
                str(getattr(row, field))
    assert len(queries) == 0


def test_task_list_editable_and_bulk_actions(admin_client):
    target = url(Task, "changelist")
    response = admin_client.get(target)
    formset = response.context["cl"].formset
    data = {
        "form-TOTAL_FORMS": formset.total_form_count(),
        "form-INITIAL_FORMS": formset.initial_form_count(),
        "_save": "Сохранить",
    }
    for index, form in enumerate(formset.forms):
        data[f"form-{index}-id"] = form.instance.pk
        data[f"form-{index}-status"] = Task.Status.COMPLETED
    assert admin_client.post(target, data).status_code == 302
    assert all(Task.objects.values_list("is_completed", flat=True))
    ids = list(Task.objects.values_list("pk", flat=True))
    for action, selected, expected in [
        ("cancel_tasks", ids[:2], Task.Status.CANCELLED),
        ("restore_tasks", ids, Task.Status.ACTIVE),
    ]:
        response = admin_client.post(
            target,
            {
                "action": action,
                "_selected_action": selected,
            },
        )
        assert response.status_code == 302
        assert set(
            Task.objects.filter(pk__in=ids[:2]).values_list(
                "status",
                "is_completed",
            )
        ) == {(expected, False)}
    assert Task.objects.get(pk=ids[2]).status == Task.Status.COMPLETED


@pytest.mark.parametrize(
    "field,value,error",
    [
        ("category", 2, "category"),
        ("user", 2, "user"),
        ("remind_at_0", "2030-01-01", "time"),
    ],
)
def test_reminder_edit_rejects_incompatible_relations(
    admin_client,
    field,
    value,
    error,
):
    original = Reminder.objects.values().get(pk=1)
    response = admin_client.post(
        url(Reminder, "change", 1),
        reminder_data(**{field: value}),
    )
    assert response.status_code == 200
    assert error in response.context["adminform"].form.errors
    assert Reminder.objects.values().get(pk=1) == original


@pytest.mark.parametrize("field,value", [("category", 2), ("user", 2)])
def test_task_edit_cannot_break_existing_reminders(admin_client, field, value):
    task = Task.objects.get(pk=1)
    response = admin_client.post(
        url(Task, "change", task.pk),
        {
            "title": task.title,
            "description": task.description,
            "user": task.user_id,
            "category": task.category_id,
            "status": task.status,
            field: value,
        },
    )
    assert response.status_code == 200
    assert field in response.context["adminform"].form.errors
    task.refresh_from_db()
    assert getattr(task, f"{field}_id") == 1


def test_time_edit_cannot_break_existing_reminders(admin_client):
    time = Time.objects.get(pk=1)
    changed = timezone.localtime(time.moment + timedelta(days=1))
    response = admin_client.post(
        url(Time, "change", time.pk),
        {
            "label": time.label,
            "moment_0": changed.strftime("%Y-%m-%d"),
            "moment_1": changed.strftime("%H:%M:%S"),
        },
    )
    assert response.status_code == 200
    assert "moment" in response.context["adminform"].form.errors
    time.refresh_from_db()
    assert time.moment != changed


@pytest.mark.parametrize("model", (User, Category))
@pytest.mark.parametrize("new_parent", (False, True))
def test_inline_validation_is_atomic(admin_client, model, new_parent):
    parent = model.objects.get(pk=2)
    target = (
        url(model, "add") if new_parent else url(model, "change", parent.pk)
    )
    parent_data = (
        {"name": "Новый родитель"} if new_parent else {"name": parent.name}
    )
    if model is User:
        parent_data["email"] = (
            "new-parent@example.org" if new_parent else parent.email
        )
    else:
        parent_data["description"] = ""
    # У существующего родителя очищаем напоминания в рамках тестовой
    # транзакции.
    if not new_parent:
        parent.reminders.all().delete()
    values = reminder_data()
    values.pop(model._meta.model_name)
    response = admin_client.post(
        target,
        {
            **parent_data,
            "reminders-TOTAL_FORMS": 1,
            "reminders-INITIAL_FORMS": 0,
            **{f"reminders-0-{key}": value for key, value in values.items()},
        },
    )
    assert response.status_code == 200
    formset = response.context["inline_admin_formsets"][0].formset
    assert model._meta.model_name in formset.forms[0].errors
    assert not Reminder.objects.filter(text="Проверка Admin").exists()
    if new_parent:
        assert not model.objects.filter(name="Новый родитель").exists()


def test_valid_create_readonly_and_autocomplete(admin_client):
    target = url(Task, "add")
    response = admin_client.post(
        target,
        {
            "title": "Создано в Admin",
            "description": "",
            "category": 1,
            "user": 1,
            "status": Task.Status.COMPLETED,
            "is_completed": "",
        },
    )
    assert response.status_code == 302
    assert Task.objects.get(title="Создано в Admin").is_completed
    response = admin_client.post(
        url(Reminder, "add"),
        reminder_data(
            user="",
            task="",
            time="",
        ),
    )
    assert response.status_code == 302
    reminder = Reminder.objects.get(text="Проверка Admin")
    assert reminder.user_id is reminder.task_id is reminder.time_id is None
    response = admin_client.get(
        reverse("admin:autocomplete"),
        {
            "app_label": "planner",
            "model_name": "task",
            "field_name": "user",
            "term": User.objects.get(pk=1).email,
        },
    )
    assert response.status_code == 200
    assert [row["id"] for row in response.json()["results"]] == ["1"]


def test_filters_date_hierarchy_and_pagination(admin_client):
    task = Task.objects.get(pk=1)
    Task.objects.filter(pk=task.pk).update(status=Task.Status.CANCELLED)
    response = admin_client.get(
        url(Task, "changelist"),
        {
            "status__exact": Task.Status.CANCELLED,
        },
    )
    assert [row.pk for row in response.context["cl"].result_list] == [task.pk]
    moment = timezone.localtime(Reminder.objects.get(pk=1).remind_at)
    response = admin_client.get(
        url(Reminder, "changelist"),
        {
            "remind_at__year": moment.year,
            "remind_at__month": moment.month,
            "remind_at__day": moment.day,
        },
    )
    rows = list(response.context["cl"].result_list)
    assert rows and all(
        timezone.localtime(row.remind_at).date() == moment.date()
        for row in rows
    )
    for index in range(26):
        Task.objects.create(
            title=f"Пагинация {index:02}",
            user_id=1,
            category_id=1,
        )
    response = admin_client.get(url(Task, "changelist"))
    changelist = response.context["cl"]
    assert changelist.paginator.per_page == 25
    assert len(changelist.result_list) == 25
    titles = [row.title for row in changelist.result_list]
    assert titles == sorted(titles)
    response = admin_client.get(url(Task, "changelist"), {"p": 2})
    assert len(response.context["cl"].result_list) == 4


@pytest.mark.parametrize("model", (User, Category))
def test_valid_inline_edit(admin_client, model):
    parent = model.objects.get(pk=1)
    response = admin_client.get(url(model, "change", parent.pk))
    formset = response.context["inline_admin_formsets"][0].formset
    data = {
        "name": parent.name,
        "reminders-TOTAL_FORMS": formset.total_form_count(),
        "reminders-INITIAL_FORMS": formset.initial_form_count(),
    }
    if model is User:
        data["email"] = parent.email
    else:
        data.update(description=parent.description, slug="forged-slug")
    for index, form in enumerate(formset.forms):
        reminder = form.instance
        moment = timezone.localtime(reminder.remind_at)
        values = {
            "id": reminder.pk,
            "text": "Изменено inline",
            "category": reminder.category_id,
            "user": reminder.user_id or "",
            "task": reminder.task_id or "",
            "time": reminder.time_id or "",
            "remind_at_0": moment.strftime("%Y-%m-%d"),
            "remind_at_1": moment.strftime("%H:%M:%S"),
        }
        data.update({f"reminders-{index}-{k}": v for k, v in values.items()})
    assert (
        admin_client.post(url(model, "change", parent.pk), data).status_code
        == 302
    )
    assert parent.reminders.filter(text="Изменено inline").exists()
    if model is Category:
        parent.refresh_from_db()
        assert parent.slug != "forged-slug"


def test_view_only_staff_cannot_run_bulk_actions():
    account = get_user_model().objects.create(
        username="viewer",
        is_staff=True,
    )
    account.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="planner",
            codename="view_task",
        )
    )
    client = Client()
    client.force_login(account)
    target = url(Task, "changelist")
    response = client.get(target)
    assert response.status_code == 200
    assert response.context["cl"].formset is None
    original = list(
        Task.objects.order_by("pk").values_list("status", flat=True)
    )
    for action in ("cancel_tasks", "restore_tasks"):
        client.post(target, {"action": action, "_selected_action": [1, 2, 3]})
    assert (
        list(Task.objects.order_by("pk").values_list("status", flat=True))
        == original
    )
