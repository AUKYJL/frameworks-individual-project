"""Каркас HTML-страниц и главная страница ПР5."""

from html import escape

from django.http import HttpResponse
from django.views.decorators.http import require_GET
from django.urls import reverse

from project_data import load_project_data


NAVIGATION = (
    ("Главная", "index"),
    ("Напоминания", "planner:reminder_list"),
    ("Задачи", "planner:task_list"),
    ("Категории", "planner:category_list"),
    ("Пользователи", "planner:user_list"),
    ("Время", "planner:time_list"),
)


def page(title: str, content: str, active: str = "") -> str:
    """HTML-обёртка с Bootstrap 5.3 и навигацией (без шаблонов, ПР5)."""
    bootstrap = (
        "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3"
        "/dist/css/bootstrap.min.css"
    )
    links = ""
    for name, route in NAVIGATION:
        cls = "active" if route == active else ""
        links += (
            f'<a class="nav-link {cls}" href="{reverse(route)}">'
            f"{escape(name)}</a>"
        )
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)} · Сервис напоминаний</title>
  <link rel="stylesheet" href="{bootstrap}">
  <style>
    body {{ background: #f5f7fb; color: #18273e; }}
    .brand {{ font-weight: 750; letter-spacing: -.6px; }}
    .nav-link {{ border-radius: .6rem; }}
    .nav-link.active {{ background: #eaf0ff; color: #153c9b; }}
    .card {{ border: 1px solid #e4e9f1; border-radius: .9rem; }}
    .hero {{ border-radius: 1rem; background: #eaf0ff; }}
    .entity-item {{ border-left: 3px solid #9bb7f2; }}
    .muted-label {{ font-size: .86rem; color: #66758c; }}
    .value {{ overflow-wrap: anywhere; }}
  </style>
</head>
<body>
  <header class="bg-white border-bottom mb-4">
    <nav class="container navbar navbar-expand-lg">
      <a class="navbar-brand brand" href="{reverse('index')}">
        ⏰ Reminderly
      </a>
      <div class="d-flex flex-wrap gap-1 ms-lg-auto">{links}</div>
    </nav>
  </header>
  <main class="container pb-5">{content}</main>
  <footer class="border-top py-3 text-center text-muted small">
    Практическая работа № 5 · Django 5.2 · Данные из JSON
  </footer>
</body>
</html>"""


@require_GET
def index(request):
    """Главная: описание и живые счётчики по JSON-данным ПР3/ПР5."""
    try:
        data = load_project_data()
    except ValueError:
        return HttpResponse(
            page("Ошибка данных", "<h1>Не удалось загрузить JSON.</h1>"),
            status=500,
        )
    sections = (
        ("Напоминания", "reminder_list", len(data.reminders),
         "События и сроки"),
        ("Задачи", "task_list", len(data.tasks), "Дела пользователей"),
        ("Категории", "category_list", len(data.categories),
         "Справочник категорий"),
        ("Пользователи", "user_list", len(data.users), "Авторы задач"),
        ("Время", "time_list", len(data.times), "Плановые моменты"),
    )
    cards = ""
    for label, name, count, description in sections:
        url = reverse(f"planner:{name}")
        cards += f"""
        <div class="col-sm-6 col-lg-4">
          <a class="text-decoration-none" href="{url}">
            <div class="card h-100 shadow-sm">
              <div class="card-body">
                <span class="muted-label">{escape(label)}</span>
                <h2 class="h3 my-2">{count}</h2>
                <p class="text-secondary mb-0">{escape(description)} →</p>
              </div>
            </div>
          </a>
        </div>"""
    content = f"""
    <div class="hero p-4 p-md-5 mb-4">
      <span class="text-primary fw-semibold">Мой учебный проект</span>
      <h1 class="display-5 fw-bold mt-2">Сервис напоминаний</h1>
      <p class="lead mb-0">Удобный просмотр напоминаний, задач,
        категорий, пользователей и времени через Django.</p>
    </div>
    <h2 class="h4 mb-3">Разделы проекта</h2>
    <div class="row g-3">{cards}</div>
    <p class="text-muted mt-4">ПР5: страницы доступны только для просмотра.
      Изменение данных остаётся в консольном приложении.</p>
    """
    return HttpResponse(page("Главная", content, active="index"))


def page_not_found(request, exception):
    """Единая пользовательская 404-страница."""
    content = f"""
    <div class="card mt-5"><div class="card-body p-5">
      <h1>404 — страница не найдена</h1>
      <p>Проверьте адрес или вернитесь на главную.</p>
      <a class="btn btn-primary" href="{reverse('index')}">На главную</a>
    </div></div>"""
    return HttpResponse(page("404", content), status=404)
