"""Административная панель предметных моделей Reminderly."""

from django.contrib import admin, messages

from planner.models import Category, Reminder, Task, Time, User


class ReminderInline(admin.TabularInline):
    model = Reminder
    extra = 0
    autocomplete_fields = ("category", "user", "task", "time")
    show_change_link = True

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            "category", "user", "task", "time",
        )


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "email")
    list_display_links = ("id", "name")
    search_fields = ("name", "email")
    list_filter = ("tasks__status",)
    ordering = ("name", "id")
    list_per_page = 25
    inlines = (ReminderInline,)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug", "description")
    list_display_links = ("id", "name")
    search_fields = ("name", "description", "slug")
    list_filter = ("tasks__status",)
    ordering = ("name", "id")
    list_per_page = 25
    readonly_fields = ("slug",)
    inlines = (ReminderInline,)


@admin.register(Time)
class TimeAdmin(admin.ModelAdmin):
    list_display = ("id", "label", "moment")
    list_display_links = ("id", "label")
    search_fields = ("label",)
    list_filter = ("moment",)
    ordering = ("moment", "id")
    list_per_page = 25


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "user", "category",
                    "status", "is_completed")
    list_display_links = ("id", "title")
    search_fields = ("title", "description", "user__name", "user__email",
                     "category__name", "reminders__text")
    list_filter = ("status", "category", "user")
    ordering = ("title", "id")
    list_per_page = 25
    list_editable = ("status",)
    readonly_fields = ("is_completed",)
    autocomplete_fields = ("user", "category")
    list_select_related = ("user", "category")
    actions = ("cancel_tasks", "restore_tasks")

    @admin.action(
        description="Отменить выбранные задачи", permissions=["change"],
    )
    def cancel_tasks(self, request, queryset):
        count = queryset.update(status=Task.Status.CANCELLED)
        self.message_user(
            request, f"Отменено задач: {count}.", messages.SUCCESS)

    @admin.action(
        description="Восстановить выбранные задачи", permissions=["change"],
    )
    def restore_tasks(self, request, queryset):
        count = queryset.cancelled().update(status=Task.Status.ACTIVE)
        self.message_user(
            request, f"Восстановлено задач: {count}.", messages.SUCCESS,
        )


@admin.register(Reminder)
class ReminderAdmin(admin.ModelAdmin):
    list_display = ("id", "text", "category", "user",
                    "task", "time", "remind_at")
    list_display_links = ("id", "text")
    search_fields = ("text", "category__name", "user__name", "user__email",
                     "task__title", "task__description", "task__user__name",
                     "task__user__email", "time__label")
    list_filter = ("category", "user", "task__status", "remind_at")
    ordering = ("-remind_at", "-id")
    list_per_page = 25
    autocomplete_fields = ("category", "user", "task", "time")
    date_hierarchy = "remind_at"
    list_select_related = ("category", "user", "task", "time")


admin.site.site_header = "Reminderly — управление напоминаниями"
admin.site.site_title = "Администрирование Reminderly"
admin.site.index_title = "Управление данными Reminderly"
