"""Предметные модели Reminderly (ПР9), отдельно от auth.User."""

from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils.text import slugify


class User(models.Model):
    class Meta:
        verbose_name = "Пользователь сервиса"
        verbose_name_plural = "Пользователи сервиса"

    name = models.CharField("Имя", max_length=120)
    email = models.EmailField("Электронная почта", unique=True)

    def __str__(self):
        return self.name


class Category(models.Model):
    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"

    name = models.CharField("Название", max_length=100, unique=True)
    description = models.TextField("Описание", blank=True, default="")

    slug = models.SlugField(
        "Адрес категории", max_length=120, unique=True, blank=True,
    )

    def save(self, *args, **kwargs):
        if not self.slug:
            # Транслитерация сохраняет читаемость русских названий в ASCII URL.
            alphabet = "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"
            latin = (
                "a b v g d e yo zh z i y k l m n o p r s t u f kh ts ch sh "
                "shch _ y _ e yu ya"
            ).split()
            table = dict(zip(alphabet, (x if x != "_" else "" for x in latin)))
            base = slugify("".join(table.get(c, c) for c in self.name.lower()))
            base = base[:120].rstrip("-") or "category"
            # Числа и new зарезервированы прежними ID URL и формой создания.
            if base.isdecimal() or base == "new":
                base = f"category-{base}"[:120]
            slug, number = base, 2
            rows = type(self).objects.using(
                kwargs.get("using") or self._state.db,
            )
            while rows.exclude(pk=self.pk).filter(slug=slug).exists():
                suffix = f"-{number}"
                slug = base[:120 - len(suffix)].rstrip("-") + suffix
                number += 1
            self.slug = slug
            if kwargs.get("update_fields") is not None:
                kwargs["update_fields"] = {
                    *kwargs["update_fields"], "slug",
                }
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse(
            "planner:category_detail_slug", kwargs={"slug": self.slug},
        )

    def __str__(self):
        return self.name


class Time(models.Model):
    class Meta:
        verbose_name = "Время"
        verbose_name_plural = "Время"

    label = models.CharField("Название", max_length=120)
    moment = models.DateTimeField("Дата и время")

    def clean(self):
        super().clean()
        if self.pk and self.moment and self.reminders.exclude(
            remind_at=self.moment,
        ).exists():
            raise ValidationError({
                "moment": "Время связано с напоминаниями. "
                "Сначала измените время в связанных напоминаниях.",
            })

    def __str__(self):
        return self.label


class TaskQuerySet(models.QuerySet):
    def active(self):
        return self.filter(status=self.model.Status.ACTIVE)

    def completed(self):
        return self.filter(status=self.model.Status.COMPLETED)

    def cancelled(self):
        return self.filter(status=self.model.Status.CANCELLED)

    def for_date(self, day):
        return self.filter(reminders__remind_at__date=day).distinct()


class Task(models.Model):
    class Meta:
        verbose_name = "Задача"
        verbose_name_plural = "Задачи"

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "В работе"
        COMPLETED = "COMPLETED", "Выполнено"
        CANCELLED = "CANCELLED", "Отменено"

    objects = TaskQuerySet.as_manager()

    title = models.CharField("Название задачи", max_length=200)
    description = models.TextField("Описание", blank=True, default="")
    user = models.ForeignKey(
        User, verbose_name="Пользователь",
        on_delete=models.PROTECT, related_name="tasks",
    )
    category = models.ForeignKey(
        Category, verbose_name="Категория",
        on_delete=models.PROTECT, related_name="tasks",
    )
    status = models.CharField(
        "Статус", max_length=9, choices=Status.choices, default=Status.ACTIVE,
    )
    is_completed = models.GeneratedField(
        verbose_name="Выполнено",
        expression=models.Case(
            models.When(status=Status.COMPLETED, then=models.Value(True)),
            default=models.Value(False), output_field=models.BooleanField(),
        ),
        output_field=models.BooleanField(), db_persist=True,
    )

    def clean(self):
        super().clean()
        if not self.pk:
            return
        errors = {}
        related = self.reminders.all()
        if self.category_id and related.exclude(
            category_id=self.category_id,
        ).exists():
            errors["category"] = (
                "Эта задача связана с напоминанием другой категории. "
                "Сначала измените связанные напоминания."
            )
        if self.user_id and related.filter(user__isnull=False).exclude(
            user_id=self.user_id,
        ).exists():
            errors["user"] = (
                "Эта задача связана с напоминанием другого пользователя. "
                "Сначала измените связанные напоминания."
            )
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return self.title


class Reminder(models.Model):
    class Meta:
        verbose_name = "Напоминание"
        verbose_name_plural = "Напоминания"

    text = models.TextField("Текст напоминания")
    category = models.ForeignKey(
        Category, verbose_name="Категория",
        on_delete=models.PROTECT, related_name="reminders",
    )
    remind_at = models.DateTimeField("Дата напоминания", db_index=True)
    user = models.ForeignKey(
        User, verbose_name="Пользователь",
        on_delete=models.PROTECT, related_name="reminders",
        null=True, blank=True,
    )
    task = models.ForeignKey(
        Task, verbose_name="Задача",
        on_delete=models.PROTECT, related_name="reminders",
        null=True, blank=True,
    )
    time = models.ForeignKey(
        Time, verbose_name="Связанное время",
        on_delete=models.PROTECT, related_name="reminders",
        null=True, blank=True,
    )

    def clean(self):
        super().clean()
        errors = {}
        task = Task.objects.filter(pk=self.task_id).first()
        if (task and (self.category_id or getattr(self, "category", None))
                and task.category_id != self.category_id):
            errors["category"] = (
                "Категория должна совпадать с категорией выбранной задачи."
            )
        if (task and (self.user_id or self.user is not None)
                and task.user_id != self.user_id):
            errors["user"] = (
                "Пользователь должен совпадать "
                "с пользователем выбранной задачи."
            )
        time = Time.objects.filter(pk=self.time_id).first()
        if time and self.remind_at and time.moment != self.remind_at:
            errors["time"] = (
                "Момент выбранного времени должен совпадать "
                "с датой и временем напоминания."
            )
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return self.text
