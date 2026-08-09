from history.models import TabView


def reset_tab_views(logical_question, tab_type, exclude_user=None):
    """Удаляет записи о просмотрах вкладки для всех, кроме указанного пользователя."""
    qs = TabView.objects.filter(
        logical_question=logical_question,
        tab_type=tab_type
    )
    if exclude_user:
        qs = qs.exclude(user=exclude_user)
    qs.delete()