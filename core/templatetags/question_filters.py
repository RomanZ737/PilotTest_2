from django import template

register = template.Library()


@register.filter
def get_border_color(item):
    """Возвращает цвет рамки в зависимости от статуса вопроса."""
    # Черновик
    if hasattr(item, 'original_question'):
        return 'dark'

    # Активный вопрос
    if hasattr(item, 'is_published'):
        if item.is_archived:
            return 'secondary'
        if item.is_published:
            return 'success'
        return 'warning'

    # Перефраз
    return 'info'


@register.filter
def get_action_color(action_type):
    """Возвращает цвет бейджа для действия."""
    colors = {
        'published': 'success',
        'unpublished': 'warning',
        'created': 'info',
        'updated_field': 'primary',
        'archived': 'secondary',
        'restored': 'success',
    }
    return colors.get(action_type, 'secondary')