"""Маршрутизация: основной URL-файл распределяет запросы по приложениям."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("homepage.urls")),
    path("", include("planner.urls")),
]

handler404 = "homepage.views.page_not_found"

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL, document_root=settings.MEDIA_ROOT,
    )

if settings.DEBUG_TOOLBAR_ENABLED:
    urlpatterns += [path("__debug__/", include("debug_toolbar.urls"))]
