"""View-функции ПР5: загрузка объектов, поиск по ID и HTML-ответы."""

from datetime import datetime
from html import escape

from django.http import HttpResponse
from django.views.decorators.http import require_GET
from django.urls import reverse

from homepage.views import page
from project_data import load_project_data


def _html(value) -> str:
    return escape(str(value))


def _link(route: str, item_id: int, title: str) -> str:
    url = reverse(f"planner:{route}", args=[item_id])
    return f'<a href="{url}">{_html(title)}</a>'


def _list_response(title: str, description: str, rows: list,
                   route: str, empty: str = "Записей пока нет"):
    if rows:
        body = '<div class="list-group">' + "".join(rows) + '</div>'
    else:
        body = f'<div class="alert alert-info">{_html(empty)}</div>'
    content = (
        f'<h1 class="mb-2">{_html(title)}</h1>'
        f'<p class="text-muted mb-4">{_html(description)}</p>{body}'
    )
    return HttpResponse(page(title, content, active=f"planner:{route}"))


def _item_row(primary: str, subtitle: str = "", badge: str = "") -> str:
    return f"""
    <div class="list-group-item entity-item py-3 px-4">
      <div class="d-flex justify-content-between flex-wrap gap-2">
        <div><div class="fw-semibold value">{primary}</div>
        <div class="small text-muted mt-1">{subtitle}</div></div>
        {badge}
      </div>
    </div>"""


def _badge(text: str, color: str = "secondary") -> str:
    return f'<span class="badge text-bg-{color}">{_html(text)}</span>'


def _details(title: str, fields: list[tuple[str, str]],
             list_route: str) -> HttpResponse:
    items = "".join(
        f'<dt class="col-sm-3 text-muted">{_html(label)}</dt>'
        f'<dd class="col-sm-9 value">{value}</dd>'
        for label, value in fields
    )
    url = reverse(f"planner:{list_route}")
    content = f"""
    <h1 class="h2 mb-4">{_html(title)}</h1>
    <div class="card shadow-sm"><div class="card-body p-4">
      <dl class="row mb-0 gy-2">{items}</dl>
    </div></div>
    <a class="btn btn-outline-primary mt-4" href="{url}">
      ← Вернуться к списку
    </a>"""
    return HttpResponse(page(title, content, active=f"planner:{list_route}"))


def _missing(name: str, route: str) -> HttpResponse:
    content = f"""
    <h1 class="text-danger">{_html(name)} не найдено</h1>
    <a class="btn btn-outline-primary" href="{reverse('planner:' + route)}">
      Вернуться к списку
    </a>"""
    return HttpResponse(page("Объект не найден", content), status=404)


def _data_or_error():
    try:
        return load_project_data()
    except ValueError:
        return HttpResponse(page(
            "Ошибка данных",
            "<h1>Ошибка чтения данных</h1>"
            "<p>Проверьте содержимое JSON-файлов.</p>",
        ), status=500)


@require_GET
def reminders(request):
    data = _data_or_error()
    if isinstance(data, HttpResponse):
        return data
    now = datetime.now()
    rows = []
    for item in sorted(data.reminders, key=lambda r: r.remind_at):
        status = item.get_status(now)
        color = "success" if status == "актуально" else "secondary"
        rows.append(_item_row(
            _link("reminder_detail", item.id, item.text),
            f"{_html(item.category)} · "
            f"{item.remind_at:%d.%m.%Y %H:%M} · №{item.id}",
            _badge(status, color),
        ))
    return _list_response(
        "Напоминания", "Список загружен из data/reminders.json.",
        rows, "reminder_list",
    )


@require_GET
def reminder_detail(request, reminder_id: int):
    data = _data_or_error()
    if isinstance(data, HttpResponse):
        return data
    item = data.by_id(data.reminders, reminder_id)
    if item is None:
        return _missing("Напоминание", "reminder_list")
    category = data.category_for_reminder(item)
    user = data.by_id(data.users, item.user_id)
    task = data.by_id(data.tasks, item.task_id)
    time = data.by_id(data.times, item.time_id)
    fields = [
        ("ID", str(item.id)),
        ("Текст", _html(item.text)),
        ("Категория", _link("category_detail", category.id, category.name)),
        ("Дата и время", f"{item.remind_at:%d.%m.%Y %H:%M}"),
        ("Статус", _badge(item.get_status(datetime.now()))),
    ]
    if user is not None:
        fields.append(("Пользователь", _link(
            "user_detail", user.id, user.name,
        )))
    if task is not None:
        fields.append(("Задача", _link("task_detail", task.id, task.title)))
    if time is not None:
        fields.append(("Время", _link("time_detail", time.id, time.label)))
    return _details(f"Напоминание №{item.id}", fields, "reminder_list")


@require_GET
def users(request):
    data = _data_or_error()
    if isinstance(data, HttpResponse):
        return data
    rows = [
        _item_row(
            _link("user_detail", user.id, user.name),
            f"{_html(user.email)} · №{user.id}",
        )
        for user in data.users
    ]
    return _list_response(
        "Пользователи", "Отдельные объекты User из data/users.json.",
        rows, "user_list",
    )


@require_GET
def user_detail(request, user_id: int):
    data = _data_or_error()
    if isinstance(data, HttpResponse):
        return data
    user = data.by_id(data.users, user_id)
    if user is None:
        return _missing("Пользователь", "user_list")
    user_tasks = [task for task in data.tasks if task.user_id == user.id]
    user_reminders = [
        reminder for reminder in data.reminders
        if reminder.user_id == user.id
    ]
    fields = [
        ("ID", str(user.id)),
        ("Имя", _html(user.name)),
        ("Email", _html(user.email)),
        ("Задачи", ", ".join(
            _link("task_detail", t.id, t.title) for t in user_tasks
        ) or "Нет задач"),
        ("Напоминания", ", ".join(
            _link("reminder_detail", r.id, r.text)
            for r in user_reminders
        ) or "Нет напоминаний"),
    ]
    return _details(user.name, fields, "user_list")


@require_GET
def categories(request):
    data = _data_or_error()
    if isinstance(data, HttpResponse):
        return data
    rows = [
        _item_row(
            _link("category_detail", c.id, c.name),
            _html(c.description),
        )
        for c in data.categories
    ]
    return _list_response(
        "Категории", "Справочник из data/categories.json.",
        rows, "category_list",
    )


@require_GET
def category_detail(request, category_id: int):
    data = _data_or_error()
    if isinstance(data, HttpResponse):
        return data
    category = data.by_id(data.categories, category_id)
    if category is None:
        return _missing("Категория", "category_list")
    linked_tasks = [
        task for task in data.tasks if task.category_id == category.id
    ]
    linked_reminders = [
        reminder for reminder in data.reminders
        if reminder.category == category.name
    ]
    return _details(category.name, [
        ("ID", str(category.id)),
        ("Описание", _html(category.description)),
        ("Задачи", ", ".join(
            _link("task_detail", t.id, t.title) for t in linked_tasks
        ) or "Нет задач"),
        ("Напоминания", ", ".join(
            _link("reminder_detail", r.id, r.text)
            for r in linked_reminders
        ) or "Нет напоминаний"),
    ], "category_list")


@require_GET
def times(request):
    data = _data_or_error()
    if isinstance(data, HttpResponse):
        return data
    rows = [
        _item_row(
            _link("time_detail", item.id, item.label),
            f"{item.moment:%d.%m.%Y %H:%M} · №{item.id}",
        )
        for item in data.times
    ]
    return _list_response(
        "Время", "Планируемые моменты из data/times.json.",
        rows, "time_list",
    )


@require_GET
def time_detail(request, time_id: int):
    data = _data_or_error()
    if isinstance(data, HttpResponse):
        return data
    item = data.by_id(data.times, time_id)
    if item is None:
        return _missing("Время", "time_list")
    linked = [
        reminder for reminder in data.reminders
        if reminder.time_id == item.id
    ]
    return _details(item.label, [
        ("ID", str(item.id)),
        ("Название", _html(item.label)),
        ("Момент", f"{item.moment:%d.%m.%Y %H:%M}"),
        ("Напоминания", ", ".join(
            _link("reminder_detail", r.id, r.text) for r in linked
        ) or "Нет напоминаний"),
    ], "time_list")


@require_GET
def tasks(request):
    data = _data_or_error()
    if isinstance(data, HttpResponse):
        return data
    rows = []
    for task in data.tasks:
        user = data.by_id(data.users, task.user_id)
        category = data.by_id(data.categories, task.category_id)
        rows.append(_item_row(
            _link("task_detail", task.id, task.title),
            f"{_html(user.name)} · {_html(category.name)} · №{task.id}",
            _badge(
                "Выполнено" if task.is_completed else "В работе",
                "success" if task.is_completed else "primary",
            ),
        ))
    return _list_response(
        "Задачи", "Объекты Task из data/tasks.json.",
        rows, "task_list",
    )


@require_GET
def task_detail(request, task_id: int):
    data = _data_or_error()
    if isinstance(data, HttpResponse):
        return data
    item = data.by_id(data.tasks, task_id)
    if item is None:
        return _missing("Задача", "task_list")
    user = data.by_id(data.users, item.user_id)
    category = data.by_id(data.categories, item.category_id)
    linked = [
        reminder for reminder in data.reminders
        if reminder.task_id == item.id
    ]
    return _details(item.title, [
        ("ID", str(item.id)),
        ("Название", _html(item.title)),
        ("Описание", _html(item.description)),
        ("Пользователь", _link("user_detail", user.id, user.name)),
        ("Категория", _link(
            "category_detail", category.id, category.name,
        )),
        ("Выполнение", _badge(
            "Выполнено" if item.is_completed else "В работе",
            "success" if item.is_completed else "primary",
        )),
        ("Напоминания", ", ".join(
            _link("reminder_detail", r.id, r.text) for r in linked
        ) or "Нет напоминаний"),
    ], "task_list")
