"""Маршрутизация: основной URL-файл распределяет запросы по приложениям."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("homepage.urls")),
    path("", include("planner.urls")),
]

handler404 = "homepage.views.page_not_found"
