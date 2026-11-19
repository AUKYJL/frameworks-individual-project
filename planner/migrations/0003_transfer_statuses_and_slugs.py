from django.db import migrations
from django.utils.text import slugify


def transfer(apps, schema_editor):
    alias = schema_editor.connection.alias
    tasks = apps.get_model("planner", "Task").objects.using(alias)
    tasks.filter(is_completed=False).update(status="ACTIVE")
    tasks.filter(is_completed=True).update(status="COMPLETED")
    # Замороженная транслитерация: миграция не зависит от текущих моделей.
    alphabet = "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"
    latin = (
        "a b v g d e yo zh z i y k l m n o p r s t u f kh ts ch sh "
        "shch _ y _ e yu ya"
    ).split()
    table = dict(zip(alphabet, (x if x != "_" else "" for x in latin)))
    categories = apps.get_model("planner", "Category").objects.using(alias)
    used = set(categories.exclude(slug__isnull=True).values_list(
        "slug", flat=True,
    ))
    for category in categories.order_by("pk").iterator():
        if category.slug:
            continue
        base = slugify("".join(table.get(c, c) for c in category.name.lower()))
        base = base[:120].rstrip("-") or "category"
        if base.isdecimal() or base == "new":
            base = f"category-{base}"[:120]
        slug, number = base, 2
        while slug in used:
            suffix = f"-{number}"
            slug = base[:120 - len(suffix)].rstrip("-") + suffix
            number += 1
        categories.filter(pk=category.pk).update(slug=slug)
        used.add(slug)


def reverse_statuses(apps, schema_editor):
    tasks = apps.get_model("planner", "Task").objects.using(
        schema_editor.connection.alias,
    )
    tasks.update(is_completed=False)
    tasks.filter(status="COMPLETED").update(is_completed=True)


class Migration(migrations.Migration):
    dependencies = [("planner", "0002_task_status_category_slug")]
    operations = [migrations.RunPython(transfer, reverse_statuses)]
