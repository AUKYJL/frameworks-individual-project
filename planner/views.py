"""Списки, поиск, связи и статистика через Django ORM (ПР10)."""

from datetime import datetime, timedelta
from functools import wraps

from django.conf import settings
from django.core.paginator import Paginator
from django.db import DatabaseError
from django.db.models import Count, F, IntegerField, Q, Sum
from django.db.models.functions import Cast
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_GET

from planner.forms import ReminderFilterForm, TaskFilterForm
from planner.models import Category, Reminder, Task, Time, User
from reminders import get_reminder_status


def db_page(func):
    """Показывать понятную страницу при недоступности БД."""
    @wraps(func)
    def wrapped(request, *args, **kwargs):
        try:
            return func(request, *args, **kwargs)
        except Http404:
            return render(request, "errors/not_found.html", status=404)
        except (DatabaseError, OSError):
            return render(request, "errors/data_error.html", status=500)
    return wrapped


def _now():
    now = timezone.now()
    return timezone.localtime(now) if settings.USE_TZ else now


def _status(moment, now):
    if settings.USE_TZ:
        moment = timezone.localtime(moment)
    label = get_reminder_status(moment, now)
    return {"label": label, "positive": label == "актуально"}


def _reminder_entries(rows):
    now = _now()
    return [
        {"reminder": record, "status": _status(record["remind_at"], now)}
        for record in rows
    ]


def _query(request):
    return request.GET.get("q", "").strip()[:100]


def _date_filter(request, name):
    value = request.GET.get(name, "").strip()
    if not value:
        return "", ""
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d")
        if parsed.strftime("%Y-%m-%d") != value:
            raise ValueError("Неправильная дата")
    except ValueError:
        return "", "Укажите корректную дату в формате ГГГГ-ММ-ДД."
    return value, ""


@require_GET
@db_page
def reminders(request):
    form = ReminderFilterForm(request.GET)
    # cleaned_data содержит корректные поля даже при ошибках других фильтров.
    form.is_valid()
    values = form.cleaned_data
    query = values.get("q", "")
    category = values.get("category")
    category_id = category.pk if category else 0
    before = values.get("before")
    date_error = form.errors.get("before", "")
    status = values.get("status") or "all"
    rows = Reminder.objects.all()
    if query:
        rows = rows.filter(
            Q(text__icontains=query) | Q(category__name__icontains=query)
            | Q(user__name__icontains=query)
        )
    if category_id:
        rows = rows.filter(category__id=category_id)
    if before:
        rows = rows.filter(remind_at__date__lte=before)
    minute = _now().replace(second=0, microsecond=0)
    next_minute = minute + timedelta(minutes=1)
    if status == "upcoming":
        rows = rows.filter(remind_at__gte=next_minute)
    elif status == "current":
        rows = rows.filter(remind_at__gte=minute, remind_at__lt=next_minute)
    elif status == "overdue":
        rows = rows.filter(remind_at__lt=minute)
    sortings = {
        "date": ("remind_at", "id"),
        "-date": ("-remind_at", "-id"),
        "category": ("category__name", "remind_at", "id"),
    }
    sort = values.get("sort") or "date"
    rows = rows.annotate(
        category_name=F("category__name"), user_name=F("user__name"),
    ).values("id", "text", "remind_at", "category_name", "user_name")
    page = Paginator(rows.order_by(*sortings[sort]), 5).get_page(
        request.GET.get("page")
    )
    params = request.GET.copy()
    params.pop("page", None)
    return render(request, "planner/reminder_list.html", {
        "entries": _reminder_entries(page.object_list),
        "filter_form": form,
        "query": query, "selected_category": category_id,
        "before": before, "date_error": date_error, "status": status,
        "filtered": bool(query or category_id or before or status != "all"),
        "sort": sort, "page_obj": page, "page_query": params.urlencode(),
    })


@require_GET
@db_page
def reminder_detail(request, reminder_id):
    reminder = get_object_or_404(
        Reminder.objects.select_related("category", "user", "task", "time"),
        pk=reminder_id,
    )
    return render(request, "planner/reminder_detail.html", {
        "reminder": reminder, "category": reminder.category,
        "user": reminder.user, "task": reminder.task, "time": reminder.time,
        "status": _status(reminder.remind_at, _now()),
    })


@require_GET
@db_page
def users(request):
    query = _query(request)
    rows = User.objects.all()
    if query:
        rows = rows.filter(
            Q(name__icontains=query) | Q(email__icontains=query)
        )
    return render(request, "planner/user_list.html", {
        "users": rows.order_by("name", "id"), "query": query,
    })


@require_GET
@db_page
def user_detail(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    return render(request, "planner/user_detail.html", {
        "user": user, "tasks": user.tasks.order_by("id"),
        "reminders": user.reminders.order_by("remind_at", "id"),
    })


@require_GET
@db_page
def categories(request):
    query = _query(request)
    rows = Category.objects.all()
    if query:
        rows = rows.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )
    return render(request, "planner/category_list.html", {
        "categories": rows.order_by("name", "id"), "query": query,
    })


@require_GET
@db_page
def category_detail(request, category_id=None, slug=None):
    lookup = {"slug": slug} if slug is not None else {"pk": category_id}
    category = get_object_or_404(Category, **lookup)
    return render(request, "planner/category_detail.html", {
        "category": category, "tasks": category.tasks.order_by("id"),
        "reminders": category.reminders.order_by("remind_at", "id"),
    })


@require_GET
@db_page
def times(request):
    query = _query(request)
    day, date_error = _date_filter(request, "day")
    rows = Time.objects.all()
    if query:
        rows = rows.filter(label__icontains=query)
    if day:
        rows = rows.filter(moment__date=day)
    return render(request, "planner/time_list.html", {
        "times": rows.order_by("moment", "id"), "query": query,
        "day": day, "date_error": date_error,
    })


@require_GET
@db_page
def time_detail(request, time_id):
    time = get_object_or_404(Time, pk=time_id)
    return render(request, "planner/time_detail.html", {
        "time": time, "reminders": time.reminders.order_by("id"),
    })


@require_GET
@db_page
def tasks(request):
    form = TaskFilterForm(request.GET)
    # cleaned_data содержит корректные поля даже при ошибках других фильтров.
    form.is_valid()
    values = form.cleaned_data
    query = values.get("q", "")
    status = values.get("status") or "all"
    category = values.get("category")
    category_id = category.pk if category else 0
    user = values.get("user")
    user_id = user.pk if user else 0
    day = values.get("day")
    date_error = form.errors.get("day", "")
    rows = Task.objects.select_related("user", "category")
    if query:
        rows = rows.filter(
            Q(title__icontains=query) | Q(description__icontains=query)
        )
    if status == "done":
        rows = rows.completed()
    elif status == "open":
        rows = rows.active()
    elif status == "cancelled":
        rows = rows.cancelled()
    if category_id:
        rows = rows.filter(category__id=category_id)
    if user_id:
        rows = rows.filter(user_id=user_id)
    if day:
        rows = rows.for_date(day)
    entries = [
        {"task": row, "user": row.user, "category": row.category}
        for row in rows.order_by("id")
    ]
    return render(request, "planner/task_list.html", {
        "entries": entries, "status": status,
        "query": query, "selected_category": category_id,
        "selected_user": user_id, "filter_form": form,
        "day": day, "date_error": date_error,
    })


@require_GET
@db_page
def task_detail(request, task_id):
    task = get_object_or_404(
        Task.objects.select_related("user", "category"), pk=task_id,
    )
    return render(request, "planner/task_detail.html", {
        "task": task, "user": task.user, "category": task.category,
        "reminders": task.reminders.order_by("remind_at", "id"),
    })


@require_GET
def reminder_search(request):
    """Совместимость старого URL /search/ со списком /reminders/."""
    return reminders(request)


@require_GET
@db_page
def statistics(request):
    raw = request.GET.get("min_tasks", "1")
    raw = raw.lstrip("0") or "0"
    min_tasks = (int(raw) if len(raw) <= 3 else 100) if raw.isdecimal() else 1
    min_tasks = max(1, min(min_tasks, 100))
    totals = Task.objects.aggregate(
        total_tasks=Count("id"),
        open_tasks=Count("id", filter=Q(status=Task.Status.ACTIVE)),
        cancelled_tasks=Count("id", filter=Q(status=Task.Status.CANCELLED)),
        completed_tasks=Count("id", filter=Q(status=Task.Status.COMPLETED)),
    )
    by_user = User.objects.annotate(
        task_count=Count("tasks"),
        done_count=Sum(Cast("tasks__is_completed", IntegerField()), default=0),
    ).order_by("-task_count", "name", "id")
    return render(request, "planner/statistics.html", {
        "totals": totals,
        "by_category": Category.objects.annotate(
            task_count=Count("tasks"),
            done_count=Sum(
                Cast("tasks__is_completed", IntegerField()), default=0,
            ),
        ).order_by("-task_count", "name", "id"),
        "by_user": by_user,
        "by_reminder_category": Category.objects.annotate(
            reminder_count=Count("reminders"),
        ).order_by("-reminder_count", "name", "id"),
        "busy_users": by_user.filter(task_count__gte=min_tasks),
        "min_tasks": min_tasks,
    })
