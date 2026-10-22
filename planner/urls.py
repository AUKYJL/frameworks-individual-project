"""URL-пути веб-разделов. <int:id> передаётся в соответствующий view."""

from django.urls import path
from . import views, crud_views

app_name = "planner"

urlpatterns = [
    path("search/", views.reminder_search, name="reminder_search"),
    path("statistics/", views.statistics, name="statistics"),
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
    # CREATE / UPDATE / DELETE для всех пяти сущностей. Статические URL
    # new/ и <int:id>/edit/ не пересекаются с карточками объектов.
    path("users/new/", crud_views.create_entity,
         {"entity": "users"}, name="user_create"),
    path("users/<int:item_id>/edit/", crud_views.edit_entity,
         {"entity": "users"}, name="user_edit"),
    path("users/<int:item_id>/delete/", crud_views.delete_entity,
         {"entity": "users"}, name="user_delete"),
    path("categories/new/", crud_views.create_entity,
         {"entity": "categories"}, name="category_create"),
    path("categories/<int:item_id>/edit/", crud_views.edit_entity,
         {"entity": "categories"}, name="category_edit"),
    path("categories/<int:item_id>/delete/", crud_views.delete_entity,
         {"entity": "categories"}, name="category_delete"),
    path("times/new/", crud_views.create_entity,
         {"entity": "times"}, name="time_create"),
    path("times/<int:item_id>/edit/", crud_views.edit_entity,
         {"entity": "times"}, name="time_edit"),
    path("times/<int:item_id>/delete/", crud_views.delete_entity,
         {"entity": "times"}, name="time_delete"),
    path("tasks/new/", crud_views.create_entity,
         {"entity": "tasks"}, name="task_create"),
    path("tasks/<int:item_id>/edit/", crud_views.edit_entity,
         {"entity": "tasks"}, name="task_edit"),
    path("tasks/<int:item_id>/delete/", crud_views.delete_entity,
         {"entity": "tasks"}, name="task_delete"),
    path("reminders/new/", crud_views.create_entity,
         {"entity": "reminders"}, name="reminder_create"),
    path("reminders/<int:item_id>/edit/", crud_views.edit_entity,
         {"entity": "reminders"}, name="reminder_edit"),
    path("reminders/<int:item_id>/delete/", crud_views.delete_entity,
         {"entity": "reminders"}, name="reminder_delete"),
]
