from django import template

register = template.Library()

@register.filter
def get_border_color(item):
    """Возвращает цвет рамки в зависимости от статуса вопроса."""
    if item.is_published:
        return 'success'  # зелёный
    elif hasattr(item, 'is_draft') and item.is_draft:
        return 'warning'  # жёлтый
    elif hasattr(item, 'is_paraphrase') and item.is_paraphrase:
        return 'info'     # голубой
    else:
        return 'warning'  # жёлтый


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