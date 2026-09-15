# -*- coding: utf-8 -*-

from datetime import datetime


def get_reminder_status(reminder_time, current_time):
    reminder_hour = int(reminder_time)
    current_hour = int(current_time)

    if current_hour < reminder_hour:
        return "ещё не наступило"
    elif current_hour == reminder_hour:
        return "актуально"
    else:
        return "просрочено"


def get_category_message(category):
    if category == "учёба":
        return "Не забудьте выполнить учебную задачу."
    elif category == "работа":
        return "Не забудьте выполнить рабочую задачу."
    else:
        return "Не забудьте о личном деле."


def format_reminder(user_name, reminder_text, reminder_time):
    return "{}, напоминаем: {}. Время: {}:00.".format(
        user_name, reminder_text, reminder_time
    )


user_name = "Анна"
reminder_text = "Подготовить домашнее задание"
category = "учёба"
reminder_time = "14"
current_time = "14"
today = datetime.now().strftime("%d.%m.%Y")

status = get_reminder_status(reminder_time, current_time)
category_message = get_category_message(category)
reminder = format_reminder(user_name, reminder_text, reminder_time)

print("Дата: {}".format(today))
print(reminder)
print("Категория: {}".format(category))
print(category_message)
print("Статус напоминания: {}".format(status))
