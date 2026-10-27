"""Списки, поиск, связи и статистика через Django ORM (ПР9)."""

from datetime import datetime, timedelta
from functools import wraps

from django.conf import settings
from django.core.paginator import Paginator
from django.db import DatabaseError
from django.db.models import Count, IntegerField, Q, Sum
from django.db.models.functions import Cast
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_GET

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


def _status(reminder, now):
    moment = reminder.remind_at
    if settings.USE_TZ:
        moment = timezone.localtime(moment)
    label = get_reminder_status(moment, now)
    return {"label": label, "positive": label == "актуально"}


def _reminder_entries(rows):
    now = _now()
    return [
        {"reminder": record, "status": _status(record, now)}
        for record in rows
    ]


def _query(request):
    return request.GET.get("q", "").strip()[:100]


def _selected_id(request, name):
    raw = request.GET.get(name, "0")
    return int(raw) if raw.isdecimal() and len(raw) <= 9 else 0


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
    query = _query(request)
    category_id = _selected_id(request, "category")
    before, date_error = _date_filter(request, "before")
    status = request.GET.get("status", "all")
    if status not in {"all", "upcoming", "current", "overdue"}:
        status = "all"
    rows = Reminder.objects.select_related("category", "user", "task", "time")
    if query:
        rows = rows.filter(text__icontains=query)
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
    sort = request.GET.get("sort", "date")
    if sort not in sortings:
        sort = "date"
    page = Paginator(rows.order_by(*sortings[sort]), 5).get_page(
        request.GET.get("page")
    )
    params = request.GET.copy()
    params.pop("page", None)
    return render(request, "planner/reminder_list.html", {
        "entries": _reminder_entries(page.object_list),
        "categories": Category.objects.order_by("name", "id"),
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
        "status": _status(reminder, _now()),
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
def category_detail(request, category_id):
    category = get_object_or_404(Category, pk=category_id)
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
    query = _query(request)
    status = request.GET.get("status", "all")
    if status not in ("all", "done", "open"):
        status = "all"
    category_id = _selected_id(request, "category")
    rows = Task.objects.select_related("user", "category")
    if query:
        rows = rows.filter(
            Q(title__icontains=query) | Q(description__icontains=query)
        )
    if status == "done":
        rows = rows.filter(is_completed=True)
    elif status == "open":
        rows = rows.exclude(is_completed=True)
    if category_id:
        rows = rows.filter(category__id=category_id)
    entries = [
        {"task": row, "user": row.user, "category": row.category}
        for row in rows.order_by("id")
    ]
    return render(request, "planner/task_list.html", {
        "entries": entries, "status": status,
        "query": query, "selected_category": category_id,
        "categories": Category.objects.order_by("name", "id"),
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
        completed_tasks=Sum(Cast("is_completed", IntegerField()), default=0),
    )
    totals["open_tasks"] = totals["total_tasks"] - totals["completed_tasks"]
    by_user = User.objects.annotate(
        task_count=Count("tasks"),
        done_count=Sum(Cast("tasks__is_completed", IntegerField()), default=0),
    ).order_by("-task_count", "name", "id")
    return render(request, "planner/statistics.html", {
        "totals": totals, "reminder_count": Reminder.objects.count(),
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
