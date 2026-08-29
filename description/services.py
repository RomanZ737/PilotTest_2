from .models import DescriptionPage

ACCESS_RULES = {
    'access': ['Администраторы'],
    'questions': ['Администраторы', 'Редактор', 'Супер Редактор'],
    'pilots': ['Администраторы', 'KRS'],
    'tests': ['Администраторы', 'KRS'],
    'testing': [],  # все
}

def get_available_sections(user):
    """Возвращает queryset разделов описания, доступных пользователю."""
    if not user.is_authenticated:
        return DescriptionPage.objects.none()

    if user.is_superuser:
        return DescriptionPage.objects.all()

    allowed_slugs = []
    for slug, groups in ACCESS_RULES.items():
        if not groups:  # пустой список — доступно всем
            allowed_slugs.append(slug)
        elif user.groups.filter(name__in=groups).exists():
            allowed_slugs.append(slug)

    return DescriptionPage.objects.filter(slug__in=allowed_slugs).order_by('id')