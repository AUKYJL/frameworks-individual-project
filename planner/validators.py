"""Общая проверка изображений категорий для ModelForm и Admin."""

from django.core.exceptions import ValidationError
from PIL import Image


def validate_category_image(value):
    if value.size > 5 * 1024 * 1024:
        raise ValidationError(
            "Размер изображения не должен превышать 5 МБ.",
            code="image_too_large",
        )
    position = value.tell()
    try:
        value.seek(0)
        image = Image.open(value)
        if image.format not in {"JPEG", "PNG", "WEBP"}:
            raise ValidationError(
                "Разрешены только JPEG, PNG и WebP.",
                code="invalid_image_format",
            )
        image.verify()
    except (OSError, ValueError, SyntaxError, Image.DecompressionBombError):
        raise ValidationError(
            "Загрузите корректное изображение JPEG, PNG или WebP.",
            code="invalid_image",
        )
    finally:
        value.seek(position)
