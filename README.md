# Reminderly — сервис напоминаний (ПР6)

Учебный индивидуальный проект на Python и Django 5.2. Развивается последовательно от консольной версии (ПР1–ПР3) через простые Django-страницы (ПР5) к **Django Templates** (ПР6).

**Результат ПР6:** HTML полностью вынесен из `views.py` в шаблоны, подключены базовый шаблон, наследование, `include`, контекст, циклы, условия, фильтры, именованные ссылки, собственные CSS, JavaScript и логотип. Предыдущие сущности, JSON и консольная версия сохранены.

## 1. Установка и запуск

Нужен Python 3.11+ и доступ к Python-пакетам при установке.

**macOS / Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py check
python manage.py migrate
python manage.py runserver
```

**Windows PowerShell:**

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py check
python manage.py migrate
python manage.py runserver
```

Сайт: <http://127.0.0.1:8000/>. Bootstrap подключается через CDN и требует интернета для загрузки его стилей, но собственный CSS/JS/логотип Django отдаёт локально при `DEBUG=True`. Без Bootstrap базовые страницы продолжают отображаться.

Консольная версия остаётся доступна через `python main.py`.

## 2. Предметная область и JSON

| Объект | Python-класс | Назначение |
| --- | --- | --- |
| Пользователь | `models.users.User` | Имя, email; связан с задачами и напоминаниями |
| Напоминание | `reminders.Reminder` | Текст, категория, дата/время, необязательные связи с User/Task/Time |
| Категория | `models.categories.Category` | Категория учёбы, работы или личных дел |
| Время | `models.times.Time` | Плановый момент, связанный с напоминанием |
| Задача | `models.tasks.Task` | Название, описание, владелец, категория, статус |

Данные хранятся в `data/reminders.json`, `data/users.json`, `data/categories.json`, `data/times.json`, `data/tasks.json`. Модуль `project_data.py` загружает пять коллекций, собирает Python-объекты и проверяет целостность ссылок. Старый формат напоминаний и консольное хранение из ПР3 не менялись.

`models.User` — пользователь как объект предметной области, не `django.contrib.auth.User`. Django ORM для пользовательских сущностей **пока нет**; встроенная SQLite используется лишь для служебных таблиц Django. Изменение/создание/удаление через веб-формы **не реализовано**: в ПР6 оно не требуется, это следующий этап курса. Веб-маршруты работают только по GET; POST возвращает 405.

## 3. Страницы

| URL | Отображаемые данные | Шаблон |
| --- | --- | --- |
| `/` | Главная с подсчётом объектов пяти коллекций | `homepage/index.html` |
| `/reminders/` | Список напоминаний, время и статус | `planner/reminder_list.html` |
| `/reminders/<id>/` | Текст, дата, связи с категорией, пользователем, задачей, временем | `planner/reminder_detail.html` |
| `/tasks/` | Список задач со статусами | `planner/task_list.html` |
| `/tasks/<id>/` | Задача, пользователь, категория и напоминания | `planner/task_detail.html` |
| `/users/` и `/users/<id>/` | Пользователи и их задачи/напоминания | `planner/user_*.html` |
| `/categories/` и `/categories/<id>/` | Категории и связанные объекты | `planner/category_*.html` |
| `/times/` и `/times/<id>/` | Моменты времени и связанные напоминания | `planner/time_*.html` |

Неизвестные идентификаторы возвращают HTTP **404** с `errors/not_found.html`; неизвестные адреса используют тот же шаблон при `DEBUG=False`. При ошибке чтения JSON возвращается статус **500** с `errors/data_error.html`.

## 4. Как работают Django Templates

1. В `reminder_site/settings.py` установлен `TEMPLATES[0]["DIRS"] = [BASE_DIR / "templates"]` и `APP_DIRS=True`.
2. `templates/base.html` содержит общий `<head>`, CSS, навигацию, подвал и блоки `{% block title %}` и `{% block content %}`. Все страницы расширяют его через `{% extends 'base.html' %}`.
3. Общая навигация подключена через `{% include 'includes/navigation.html' %}`. Повторяемые карточки и бейджи подключаются из `planner/templates/planner/includes/`.
4. `homepage/views.py` и `planner/views.py` получают Python-объекты и передают данные в шаблоны через `render(request, '...', context)` — **функция `page()` из ПР5 удалена**.
5. В дочерних шаблонах используются атрибуты объектов `{{ reminder.text }}`, циклы `{% for %}` и `{% empty %}`, условия `{% if %}` и фильтры `length`, `default`, `date`, `capfirst`. HTML-значения Django экранирует по умолчанию.
6. Маршруты имеют имена `homepage:index` и `planner:reminder_detail`, `planner:task_list` и т.д. Ссылки строятся через `{% url 'planner:reminder_detail' reminder.id %}`.
7. `base.html` подключает через `{% load static %}` файлы `homepage/css/style.css`, `homepage/js/main.js`, а навигация использует `homepage/img/logo.svg`. Скрипт подставляет текущий год в подвале.

## 5. Структура проекта

```text
individual-project/
├── reminder_site/                 # Django settings / urls / wsgi / asgi
├── templates/
│   ├── base.html                  # Общий HTML-каркас
│   ├── includes/navigation.html  # Общая навигация
│   └── errors/                    # 404 и ошибка JSON
├── homepage/
│   ├── views.py                   # Главная через render()
│   ├── templates/homepage/index.html
│   └── static/homepage/
│       ├── css/style.css
│       ├── js/main.js
│       └── img/logo.svg
├── planner/
│   ├── views.py                   # Получение объектов и подготовка контекста
│   └── templates/planner/        # Списки, детали, includes
├── models/                       # Пять классов предметной области
├── data/                         # Пять JSON-файлов
├── project_data.py               # Загрузка и проверка JSON-ссылок
├── reminders.py, storage.py, main.py, utils.py  # Код ПР3
├── tests/                        # Python и HTTP-тесты
├── ПЛАН_ПР5.md
├── ПЛАН_ПР6.md                   # Анализ PDF, план и чек-лист защиты
├── manage.py
└── requirements.txt
```

## 6. Проверка

```bash
python manage.py check
python -m pytest -v
python -m flake8 . --extend-exclude=venv
```

HTTP-тесты выполняются, когда установлен Django: они проверяют все страницы, шаблоны, 404, GET-only, статические ресурсы и экранирование HTML. Остальные тесты проверяют сущности, JSON и прежнюю бизнес-логику. Для проверки кастомной страницы неизвестного маршрута используйте `DJANGO_DEBUG=0 python manage.py runserver` (Windows PowerShell: `$env:DJANGO_DEBUG="0"`).

В среде сборки архива Django и flake8 установить не удалось из-за отсутствия сетевого доступа. Поэтому пройдены офлайн-тесты Python, а HTTP-тесты и `manage.py check` необходимо выполнить после установки `requirements.txt` у себя.

**Git:** изменения сохраняются в текущем репозитории коммитом с префиксом `PR6:`.

## 7. Что дальше

Переход на Django ORM и базу данных для предметных сущностей, веб-формы, CRUD, аутентификация пользователей. Материалы Яндекс Практикума («HTML и шаблоны Django», «Блогикум») проходятся отдельно на образовательной платформе.
