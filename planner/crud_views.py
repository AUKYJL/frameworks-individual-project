"""CRUD пяти предметных сущностей через Django ORM."""

from django.contrib import messages
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST

from planner.forms import FORMS
from planner.models import Category, Reminder, Task, Time, User
from planner.views import db_page


MODELS = {
    "users": User, "categories": Category, "times": Time,
    "tasks": Task, "reminders": Reminder,
}


ENTITY = {
    "users": ("Пользователь", "user"),
    "categories": ("Категория", "category"),
    "times": ("Время", "time"),
    "tasks": ("Задача", "task"),
    "reminders": ("Напоминание", "reminder"),
}


def _config(entity):
    if entity not in ENTITY:
        raise Http404("Раздел не найден")
    return ENTITY[entity]


def _urls(entity):
    _, name = _config(entity)
    return {
        "list": reverse(f"planner:{name}_list"),
        "create": reverse(f"planner:{name}_create"),
    }


def _validation_error(form, error):
    message = str(error).lower()
    if "unique" in message:
        field = "email" if "email" in form.fields else "name"
        form.add_error(field, "Такое значение уже существует.")
    elif "foreign key" in message:
        form.add_error(None, "Не найдена связанная запись. Обновите форму.")
    else:
        form.add_error(None, "Не удалось сохранить запись. Проверьте поля.")


@require_http_methods(["GET", "POST"])
@db_page
def create_entity(request, entity):
    title, name = _config(entity)
    form = FORMS[entity](
        request.POST if request.method == "POST" else None,
        request.FILES if request.method == "POST" else None,
    )
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                record = form.save()
        except IntegrityError as error:
            _validation_error(form, error)
        else:
            messages.success(request, f"{title} создан(а).")
            return redirect(
                record.get_absolute_url() if entity == "categories" else
                reverse(f"planner:{name}_detail",
                        kwargs={f"{name}_id": record.pk})
            )
    return render(request, "planner/entity_form.html", {
        "form": form, "entity": title, "action_name": "Создание",
        "back_url": _urls(entity)["list"],
    })


@require_http_methods(["GET", "POST"])
@db_page
def edit_entity(request, entity, item_id):
    title, name = _config(entity)
    record = get_object_or_404(MODELS[entity], pk=item_id)
    form = FORMS[entity](
        request.POST if request.method == "POST" else None,
        request.FILES if request.method == "POST" else None,
        instance=record,
    )
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                form.save()
        except IntegrityError as error:
            _validation_error(form, error)
        else:
            messages.success(request, f"{title} изменён(а).")
            return redirect(
                record.get_absolute_url() if entity == "categories" else
                reverse(f"planner:{name}_detail",
                        kwargs={f"{name}_id": item_id})
            )
    return render(request, "planner/entity_form.html", {
        "form": form, "entity": title, "action_name": "Редактирование",
        "back_url": (record.get_absolute_url() if entity == "categories" else
                     reverse(f"planner:{name}_detail",
                             kwargs={f"{name}_id": item_id})),
    })


@require_http_methods(["GET", "POST"])
@db_page
def delete_entity(request, entity, item_id):
    title, name = _config(entity)
    record = get_object_or_404(MODELS[entity], pk=item_id)
    error = ""
    if request.method == "POST":
        try:
            with transaction.atomic():
                record.delete()
        except (ProtectedError, IntegrityError):
            error = ("Нельзя удалить запись: на неё ссылаются другие записи. "
                     "Сначала измените или удалите связанные записи.")
        else:
            messages.success(request, f"{title} удалён(а).")
            return redirect(f"planner:{name}_list")
    return render(request, "planner/entity_confirm_delete.html", {
        "entity": title, "record": record, "error": error,
        "back_url": (record.get_absolute_url() if entity == "categories" else
                     reverse(f"planner:{name}_detail",
                             kwargs={f"{name}_id": item_id})),
    }, status=409 if error else 200)


@require_POST
@db_page
def cancel_task(request, task_id):
    task = get_object_or_404(Task, pk=task_id)
    task.cancel()
    messages.success(request, "Задача отменена.")
    return redirect("planner:task_detail", task_id=task.pk)
