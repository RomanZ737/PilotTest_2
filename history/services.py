from history.models import TabView, ActivityLog


def reset_tab_views(logical_question, tab_type, exclude_user=None):
    """Удаляет записи о просмотрах вкладки для всех, кроме указанного пользователя."""
    qs = TabView.objects.filter(
        logical_question=logical_question,
        tab_type=tab_type
    )
    if exclude_user:
        qs = qs.exclude(user=exclude_user)
    qs.delete()


def log_activity(user, entity_type, entity_id, entity_name, action_type, theme=None, description=''):
    """Создаёт запись в журнале активности."""
    return ActivityLog.objects.create(
        user=user,
        user_name=user.get_full_name() or user.username if user else '',
        entity_type=entity_type,
        entity_id=entity_id,
        entity_name=str(entity_name)[:500],
        action_type=action_type,
        theme=theme,
        description=description,
    )