"""URL-пути веб-разделов. <int:id> передаётся в соответствующий view."""

from django.urls import path
from . import views

app_name = "planner"

urlpatterns = [
    path("reminders/", views.reminders, name="reminder_list"),
    path("reminders/<int:reminder_id>/", views.reminder_detail,
         name="reminder_detail"),
    path("users/", views.users, name="user_list"),
    path("users/<int:user_id>/", views.user_detail, name="user_detail"),
    path("categories/", views.categories, name="category_list"),
    path("categories/<int:category_id>/", views.category_detail,
         name="category_detail"),
    path("times/", views.times, name="time_list"),
    path("times/<int:time_id>/", views.time_detail, name="time_detail"),
    path("tasks/", views.tasks, name="task_list"),
    path("tasks/<int:task_id>/", views.task_detail, name="task_detail"),
]
