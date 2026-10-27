"""Обычные Django Forms с выборками и проверкой связей через ORM."""

from django import forms

from planner.models import Category, Reminder, Task, Time, User


class PlainForm(forms.Form):
    """Небольшие Bootstrap-классы для HTML-форм."""

    def __init__(self, *args, item_id=None, **kwargs):
        self.item_id = item_id
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = "form-check-input"
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs["class"] = "form-select"
            else:
                field.widget.attrs["class"] = "form-control"


class UserForm(PlainForm):
    name = forms.CharField(label="Имя", max_length=120)
    email = forms.EmailField(label="Email", max_length=254)


class CategoryForm(PlainForm):
    name = forms.CharField(label="Название", max_length=100)
    description = forms.CharField(
        label="Описание", max_length=500, required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )


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


class TimeForm(PlainForm):
    label = forms.CharField(label="Название", max_length=120)
    moment = date_field("Дата и время")

    def clean(self):
        values = super().clean()
        if self.item_id and values.get("moment"):
            linked = Reminder.objects.filter(time_id=self.item_id).exclude(
                remind_at=values["moment"],
            ).exists()
            if linked:
                self.add_error(
                    "moment", "Время связано с напоминаниями. "
                    "Сначала измените время в связанных напоминаниях.",
                )
        return values


def choices(model, label_column):
    return list(model.objects.order_by(label_column, "id").values_list(
        "id", label_column,
    ))


def choice_field(label, optional=False):
    return forms.TypedChoiceField(
        label=label, choices=(), coerce=int,
        empty_value=None, required=not optional,
    )


class TaskForm(PlainForm):
    title = forms.CharField(label="Название задачи", max_length=200)
    description = forms.CharField(
        label="Описание", required=False, max_length=2000,
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    user_id = choice_field("Пользователь")
    category_id = choice_field("Категория")
    is_completed = forms.BooleanField(label="Выполнена", required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["user_id"].choices = choices(User, "name")
        self.fields["category_id"].choices = choices(
            Category, "name"
        )

    def clean(self):
        values = super().clean()
        if not self.item_id or not all(
            name in values for name in ("user_id", "category_id")
        ):
            return values
        related = Reminder.objects.filter(task_id=self.item_id)
        for reminder in related:
            if reminder.category_id != values["category_id"]:
                self.add_error(
                    "category_id", "Эта задача связана с напоминанием другой "
                    "категории. Сначала измените связанные напоминания.",
                )
                break
        for reminder in related:
            if (reminder.user_id is not None
                    and reminder.user_id != values["user_id"]):
                self.add_error(
                    "user_id", "Эта задача связана с напоминанием другого "
                    "пользователя. Сначала измените связанные напоминания.",
                )
                break
        return values


class ReminderForm(PlainForm):
    text = forms.CharField(
        label="Текст напоминания", max_length=500,
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    category_id = choice_field("Категория")
    remind_at = date_field("Дата и время напоминания")
    user_id = choice_field("Пользователь", optional=True)
    task_id = choice_field("Задача", optional=True)
    time_id = choice_field("Связанное время", optional=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category_id"].choices = choices(
            Category, "name"
        )
        self.fields["user_id"].choices = [('', 'Без пользователя')] + choices(
            User, "name"
        )
        self.fields["task_id"].choices = [('', 'Без задачи')] + choices(
            Task, "title"
        )
        self.fields["time_id"].choices = [('', 'Без связанного времени')]
        self.fields["time_id"].choices += choices(Time, "label")
        self.fields["time_id"].help_text = (
            "Необязательно. Если выбрано, его дата должна совпадать "
            "с датой напоминания."
        )
        self.fields["task_id"].help_text = (
            "Категория и пользователь выбранной задачи должны совпадать "
            "с указанными выше."
        )

    def clean(self):
        values = super().clean()
        if values.get("task_id"):
            task = Task.objects.filter(pk=values["task_id"]).first()
            if task and values.get("category_id") is not None:
                if task.category_id != values["category_id"]:
                    self.add_error(
                        "category_id", "Категория должна совпадать "
                        "с категорией выбранной задачи.",
                    )
            if task and values.get("user_id") is not None:
                if task.user_id != values["user_id"]:
                    self.add_error(
                        "user_id", "Пользователь должен совпадать "
                        "с пользователем выбранной задачи.",
                    )
        if values.get("time_id") and values.get("remind_at"):
            time = Time.objects.filter(pk=values["time_id"]).first()
            if time and time.moment != values["remind_at"]:
                self.add_error(
                    "time_id", "Момент выбранного времени должен совпадать "
                    "с датой и временем напоминания.",
                )
        return values


FORMS = {
    "users": UserForm,
    "categories": CategoryForm,
    "times": TimeForm,
    "tasks": TaskForm,
    "reminders": ReminderForm,
}


def to_initial(record):
    """Сохранить FK-идентификаторы и datetime для обычных Django Forms."""
    return {
        field.attname: getattr(record, field.attname)
        for field in record._meta.fields
    }
