"""ПР11: изображения через пользовательские формы и CategoryAdmin."""

from io import BytesIO
from importlib.util import module_from_spec, spec_from_file_location

import pytest
from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, override_settings
from django.urls import reverse
from PIL import Image

from planner.forms import CategoryForm
from planner.models import Category

pytestmark = pytest.mark.usefixtures("orm_db", "media_root")
LIMIT = 5 * 1024 * 1024


@pytest.fixture
def media_root(tmp_path):
    root = tmp_path / "media"
    with override_settings(MEDIA_ROOT=root):
        yield root


def image_file(format="PNG", name=None, size=None):
    stream = BytesIO()
    Image.new("RGB", (12, 8), "blue").save(stream, format=format)
    content = stream.getvalue()
    if size:
        content += b"\0" * (size - len(content))
    extension = "jpg" if format == "JPEG" else format.lower()
    return SimpleUploadedFile(
        name or f"category.{extension}", content,
        content_type=f"image/{extension}",
    )


@pytest.mark.parametrize("format", ["JPEG", "PNG", "WEBP"])
def test_upload_and_display(format, media_root):
    client = Client()
    target = reverse("planner:category_create")
    html = client.get(target).content.decode()
    assert 'enctype="multipart/form-data"' in html
    response = client.post(target, {
        "name": "С изображением", "description": "Описание",
        "image": image_file(format),
    })
    category = Category.objects.get(name="С изображением")
    assert response.status_code == 302
    assert response.url == category.get_absolute_url()
    assert category.image.name.startswith("categories/")
    assert (media_root / category.image.name).is_file()
    for url in (reverse("planner:category_list"), category.get_absolute_url()):
        page = client.get(url)
        assert page.status_code == 200
        assert f'src="{category.image.url}"' in page.content.decode()


def test_replace_preserve_and_clear_image(media_root):
    client = Client()
    category = Category.objects.create(name="Замена")
    target = reverse("planner:category_edit", args=[category.pk])
    data = {"name": category.name, "description": ""}
    names = []
    for format in ("PNG", "JPEG"):
        assert client.post(target, {
            **data, "image": image_file(format),
        }).status_code == 302
        category.refresh_from_db()
        names.append(category.image.name)
        assert (media_root / category.image.name).is_file()
    assert names[0] != names[1]
    assert client.post(target, data).status_code == 302
    category.refresh_from_db()
    assert category.image.name == names[1]
    assert client.post(target, {
        **data, "image-clear": "on",
    }).status_code == 302
    category.refresh_from_db()
    assert not category.image


def test_category_without_image():
    client = Client()
    assert client.post(reverse("planner:category_create"), {
        "name": "Без изображения", "description": "",
    }).status_code == 302
    category = Category.objects.get(name="Без изображения")
    assert not category.image
    page = client.get(category.get_absolute_url())
    assert "Изображение не добавлено." in page.content.decode()
    assert "Нет фото" in client.get(
        reverse("planner:category_list"),
    ).content.decode()


@pytest.mark.parametrize("kind", ["text", "spoofed", "broken", "gif", "large"])
@pytest.mark.parametrize("edit", [False, True])
def test_invalid_upload_does_not_change_database_or_storage(
    kind, edit, media_root,
):
    category = Category.objects.create(name="Сохранённая", image=image_file())
    original = category.image.name
    files = sorted(media_root.rglob("*"))
    upload = {
        "text": lambda: SimpleUploadedFile("bad.txt", b"text"),
        "spoofed": lambda: SimpleUploadedFile(
            "fake.png", b"not an image", content_type="image/png",
        ),
        "broken": lambda: SimpleUploadedFile(
            "broken.png", image_file().read()[:40], content_type="image/png",
        ),
        # Допустимые расширение и MIME не должны обходить проверку содержимого.
        "gif": lambda: image_file("GIF", name="fake.png"),
        "large": lambda: image_file(size=LIMIT + 1),
    }[kind]()
    count = Category.objects.count()
    target = (
        reverse("planner:category_edit", args=[category.pk]) if edit
        else reverse("planner:category_create")
    )
    response = Client().post(target, {
        "name": category.name if edit else "Не сохранять",
        "description": "", "image": upload,
    })
    assert response.status_code == 200
    assert "image" in response.context["form"].errors
    assert Category.objects.count() == count
    category.refresh_from_db()
    assert category.image.name == original
    assert sorted(media_root.rglob("*")) == files


def test_exact_size_limit_and_model_validation():
    form = CategoryForm({"name": "Ровно 5 МБ"}, {
        "image": image_file(size=LIMIT),
    })
    assert form.is_valid(), form.errors
    for upload in (image_file("GIF"), image_file(size=LIMIT + 1)):
        category = Category(name="Неверный файл", image=upload)
        with pytest.raises(ValidationError) as error:
            category.full_clean()
        assert "image" in error.value.message_dict


def test_admin_upload_replace_and_validation(media_root):
    account = get_user_model().objects.create(
        username="image-admin", is_staff=True, is_superuser=True,
    )
    client = Client()
    client.force_login(account)
    data = {
        "name": "Из Admin", "description": "",
        "reminders-TOTAL_FORMS": 0, "reminders-INITIAL_FORMS": 0,
    }
    target = reverse("admin:planner_category_add")
    html = client.get(target).content.decode()
    assert 'enctype="multipart/form-data"' in html
    assert client.post(target, {
        **data, "image": image_file(),
    }).status_code == 302
    category = Category.objects.get(name=data["name"])
    original = category.image.name
    target = reverse("admin:planner_category_change", args=[category.pk])
    assert client.post(target, {
        **data, "image": image_file("WEBP"),
    }).status_code == 302
    category.refresh_from_db()
    assert category.image.name != original
    assert (media_root / category.image.name).is_file()
    original = category.image.name
    for upload in (image_file("GIF"), image_file(size=LIMIT + 1)):
        response = client.post(target, {**data, "image": upload})
        assert response.status_code == 200
        assert "image" in response.context["adminform"].form.errors
        category.refresh_from_db()
        assert category.image.name == original


@pytest.mark.parametrize("debug", [True, False])
def test_media_served_only_in_debug(debug, media_root):
    upload = image_file()
    path = media_root / "categories" / upload.name
    path.parent.mkdir(parents=True)
    path.write_bytes(upload.read())
    with override_settings(DEBUG=debug, DEBUG_TOOLBAR_ENABLED=False):
        # Свежий URLconf не изменяет маршруты остальных тестов.
        spec = spec_from_file_location(
            "media_test_urls", settings.BASE_DIR / "reminder_site/urls.py",
        )
        module = module_from_spec(spec)
        spec.loader.exec_module(module)
        with override_settings(ROOT_URLCONF=module):
            response = Client().get(f"/media/categories/{upload.name}")
            assert response.status_code == (200 if debug else 404)
            if debug:
                content = b"".join(response.streaming_content)
                assert content == path.read_bytes()
            response.close()
