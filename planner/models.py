"""Предметные модели Reminderly (ПР9), отдельно от auth.User."""

from django.db import models


class User(models.Model):
    name = models.CharField(max_length=120)
    email = models.EmailField(unique=True)

    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, default="")

    def __str__(self):
        return self.name


class Time(models.Model):
    label = models.CharField(max_length=120)
    moment = models.DateTimeField()

    def __str__(self):
        return self.label


class Task(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    user = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="tasks",
    )
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="tasks",
    )
    is_completed = models.BooleanField(default=False)

    def __str__(self):
        return self.title


class Reminder(models.Model):
    text = models.TextField()
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="reminders",
    )
    remind_at = models.DateTimeField(db_index=True)
    user = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="reminders",
        null=True, blank=True,
    )
    task = models.ForeignKey(
        Task, on_delete=models.PROTECT, related_name="reminders",
        null=True, blank=True,
    )
    time = models.ForeignKey(
        Time, on_delete=models.PROTECT, related_name="reminders",
        null=True, blank=True,
    )

    def __str__(self):
        return self.text
