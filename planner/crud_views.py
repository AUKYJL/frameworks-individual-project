"""CRUD страницы для пяти предметных сущностей на sqlite3 (без ORM)."""

import sqlite3

from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from db.crud import (RelatedRecordsError, delete_item, get_item,
                     insert_item, update_item)
from planner.forms import FORMS, to_database, to_initial
from planner.views import db_page


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
    form = FORMS[entity](request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try:
            new_id = insert_item(entity, to_database(form.cleaned_data))
        except sqlite3.IntegrityError as error:
            _validation_error(form, error)
        else:
            messages.success(request, f"{title} создан(а).")
            return redirect(f"planner:{name}_detail", **{f"{name}_id": new_id})
    return render(request, "planner/entity_form.html", {
        "form": form, "entity": title, "action_name": "Создание",
        "back_url": _urls(entity)["list"],
    })


@require_http_methods(["GET", "POST"])
@db_page
def edit_entity(request, entity, item_id):
    title, name = _config(entity)
    record = get_item(entity, item_id)
    if record is None:
        raise Http404(f"{title} не найден(а)")
    form = FORMS[entity](
        request.POST if request.method == "POST" else None,
        initial=to_initial(record), item_id=item_id,
    )
    if request.method == "POST" and form.is_valid():
        try:
            update_item(entity, item_id, to_database(form.cleaned_data))
        except sqlite3.IntegrityError as error:
            _validation_error(form, error)
        else:
            messages.success(request, f"{title} изменён(а).")
            return redirect(
                f"planner:{name}_detail", **{f"{name}_id": item_id}
            )
    return render(request, "planner/entity_form.html", {
        "form": form, "entity": title, "action_name": "Редактирование",
        "back_url": reverse(
            f"planner:{name}_detail", kwargs={f"{name}_id": item_id}
        ),
    })


@require_http_methods(["GET", "POST"])
@db_page
def delete_entity(request, entity, item_id):
    title, name = _config(entity)
    record = get_item(entity, item_id)
    if record is None:
        raise Http404(f"{title} не найден(а)")
    error = ""
    if request.method == "POST":
        try:
            delete_item(entity, item_id)
        except RelatedRecordsError as exception:
            error = str(exception)
        else:
            messages.success(request, f"{title} удалён(а).")
            return redirect(f"planner:{name}_list")
    return render(request, "planner/entity_confirm_delete.html", {
        "entity": title, "record": record, "error": error,
        "back_url": reverse(
            f"planner:{name}_detail", kwargs={f"{name}_id": item_id}
        ),
    }, status=409 if error else 200)
