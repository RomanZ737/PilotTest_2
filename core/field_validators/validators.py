from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator

def validate_file_size(value, max_size_mb=2):
    """Проверка размера файла."""
    max_size_bytes = max_size_mb * 1024 * 1024
    if value.size > max_size_bytes:
        raise ValidationError(
            f'Размер файла не должен превышать {max_size_mb} МБ. '
            f'Текущий размер: {value.size / (1024 * 1024):.1f} МБ.'
        )


def validate_image(value):
    """Проверка, что файл — изображение допустимого формата и размера."""
    ext_validator = FileExtensionValidator(
        allowed_extensions=['jpg', 'jpeg', 'png', 'gif', 'webp']
    )
    ext_validator(value)
    validate_file_size(value)

