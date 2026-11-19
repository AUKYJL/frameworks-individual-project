"""ModelForm предметных сущностей с Bootstrap и проверкой напоминаний."""

from datetime import timedelta

from django import forms
from django.forms.models import ModelChoiceIterator
from django.core.exceptions import ValidationError
from django.utils import timezone

from planner.models import Category, Reminder, Task, Time, User


class AllChoiceIterator(ModelChoiceIterator):
    def __iter__(self):
        for value, label in super().__iter__():
            yield ("0" if value == "" else value), label


class FilterModelChoiceField(forms.ModelChoiceField):
    """Сохраняет GET-значение 0 для выбора всех записей."""

    iterator = AllChoiceIterator
    empty_values = [*forms.Field.empty_values, "0", 0]


class FilterForm(forms.Form):
    q = forms.CharField(label="Поиск", required=False, max_length=100,
                        widget=forms.SearchInput(attrs={
                            "id": "entity-search",
                            "aria-label": "Поиск по записям",
                        }))
    category = FilterModelChoiceField(
        label="Категория", required=False, initial="0",
        queryset=Category.objects.order_by("name", "id"),
        empty_label="Все категории",
    )

    def __init__(self, data=None, *args, **kwargs):
        if data is not None:
            data = data.copy()
            for name, field in self.base_fields.items():
                if field.initial is not None:
                    data.setdefault(name, field.initial)
        super().__init__(data, *args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = (
                "form-select" if isinstance(field.widget, forms.Select)
                else "form-control"
            )

    def clean(self):
        values = super().clean()
        for name, field in self.fields.items():
            if isinstance(field, forms.DateField) and values.get(name):
                if self.data.get(name, "").strip() != values[name].isoformat():
                    self.add_error(name, field.error_messages["invalid"])
        return values


class ReminderFilterForm(FilterForm):
    before = forms.DateField(
        label="До даты", required=False, input_formats=["%Y-%m-%d"],
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
        error_messages={
            "invalid": "Укажите корректную дату в формате ГГГГ-ММ-ДД.",
        },
    )
    status = forms.ChoiceField(
        label="Статус", required=False, initial="all", choices=[
            ("all", "Любой"), ("upcoming", "Ещё не наступило"),
            ("current", "Актуально"), ("overdue", "Просрочено"),
        ],
    )
    sort = forms.ChoiceField(
        label="Сортировка", required=False, initial="date", choices=[
            ("date", "По дате ↑"), ("-date", "По дате ↓"),
            ("category", "По категории"),
        ],
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["q"].widget.attrs["placeholder"] = (
            "Текст, категория или имя пользователя"
        )
        for name in ("category", "before", "status", "sort"):
            self.fields[name].widget.attrs["id"] = f"reminder-{name}"


class TaskFilterForm(FilterForm):
    field_order = ("q", "status", "category", "user", "day")
    status = forms.ChoiceField(
        label="Статус", required=False, initial="all", choices=[
            ("all", "Все"), ("open", "В работе"), ("done", "Выполненные"),
            ("cancelled", "Отменённые"),
        ],
    )
    user = FilterModelChoiceField(
        label="Пользователь", required=False, initial="0",
        queryset=User.objects.order_by("name", "id"),
        empty_label="Все пользователи",
    )
    day = forms.DateField(
        label="Дата напоминания", required=False, input_formats=["%Y-%m-%d"],
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
        error_messages={
            "invalid": "Укажите корректную дату в формате ГГГГ-ММ-ДД.",
        },
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["q"].widget.attrs["placeholder"] = "Название или описание"
        for name in ("status", "category", "user", "day"):
            self.fields[name].widget.attrs["id"] = f"task-{name}"


class BootstrapModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = "form-check-input"
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs["class"] = "form-select"
            else:
                field.widget.attrs["class"] = "form-control"


class UserForm(BootstrapModelForm):
    class Meta:
        model = User
        fields = ("name", "email")
        labels = {"email": "Email"}


class CategoryForm(BootstrapModelForm):
    description = forms.CharField(
        label="Описание", max_length=500, required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    class Meta:
        model = Category
        fields = ("name", "description", "image")
        widgets = {
            "image": forms.ClearableFileInput(attrs={
                "accept": "image/jpeg,image/png,image/webp",
            }),
        }


class DateTimeInput(forms.DateTimeInput):
    input_type = "datetime-local"


DATE_FORMAT = "%Y-%m-%dT%H:%M"


def date_field(label):
    return forms.DateTimeField(
        label=label,
        input_formats=[DATE_FORMAT, "%Y-%m-%dT%H:%M:%S"],
        widget=DateTimeInput(format=DATE_FORMAT),
        error_messages={"invalid": "Укажите дату и время."},
    )


class TimeForm(BootstrapModelForm):
    moment = date_field("Дата и время")

    class Meta:
        model = Time
        fields = ("label", "moment")


class TaskForm(BootstrapModelForm):
    description = forms.CharField(
        label="Описание", required=False, max_length=2000,
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    class Meta:
        model = Task
        fields = ("title", "description", "user", "category", "status")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["user"].queryset = User.objects.order_by("name", "id")
        self.fields["category"].queryset = Category.objects.order_by(
            "name", "id",
        )


def validate_reminder_text(value):
    """Напоминание должно содержать хотя бы одну букву или цифру."""
    if not any(character.isalnum() for character in value):
        raise ValidationError(
            "Текст напоминания должен содержать буквы или цифры.",
            code="invalid_reminder_text",
        )


class ReminderForm(BootstrapModelForm):
    text = forms.CharField(
        label="Текст напоминания", max_length=500,
        validators=[validate_reminder_text],
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    remind_at = date_field("Дата и время напоминания")

    class Meta:
        model = Reminder
        fields = ("text", "category", "remind_at", "user", "task", "time")
        help_texts = {
            "time": "Необязательно. Если выбрано, его дата должна совпадать "
                    "с датой напоминания.",
            "task": "Категория и пользователь выбранной задачи должны "
                    "совпадать с указанными выше.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, model, column, empty_label in (
            ("category", Category, "name", "---------"),
            ("user", User, "name", "Без пользователя"),
            ("task", Task, "title", "Без задачи"),
            ("time", Time, "label", "Без связанного времени"),
        ):
            self.fields[name].queryset = model.objects.order_by(column, "id")
            self.fields[name].empty_label = empty_label
        if self.instance._state.adding:
            self.initial.setdefault(
                "remind_at",
                (timezone.now() + timedelta(hours=1)).replace(
                    second=0, microsecond=0,
                ),
            )
        self._original_remind_at = self.instance.remind_at
        original = self._original_remind_at
        if original and (original.second or original.microsecond):
            widget = self.fields["remind_at"].widget
            widget.format = "%Y-%m-%dT%H:%M:%S"
            widget.attrs["step"] = 1
            if original.microsecond:
                widget.supports_microseconds = True
                widget.format += ".%f"
                widget.attrs["step"] = "any"

    def clean_remind_at(self):
        remind_at = self.cleaned_data["remind_at"]
        unchanged = (
            not self.instance._state.adding
            and remind_at == self._original_remind_at
        )
        if remind_at < timezone.now() and not unchanged:
            raise ValidationError(
                "Нельзя назначить напоминание на прошедшую дату."
            )
        return remind_at

    def clean(self):
        values = super().clean()
        required = ("text", "category", "user", "remind_at")
        if all(name in values for name in required):
            conflicts = Reminder.objects.filter(
                text=values["text"], category=values["category"],
                user=values["user"], remind_at=values["remind_at"],
            ).exclude(task__status__in=[
                Task.Status.CANCELLED, Task.Status.COMPLETED,
            ])
            if not self.instance._state.adding:
                conflicts = conflicts.exclude(pk=self.instance.pk)
            if conflicts.exists():
                raise ValidationError(
                    "Такое напоминание для этого пользователя и категории "
                    "на указанное время уже существует."
                )
        return values


FORMS = {
    "users": UserForm,
    "categories": CategoryForm,
    "times": TimeForm,
    "tasks": TaskForm,
    "reminders": ReminderForm,
}
