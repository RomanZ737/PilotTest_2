from history.models import ActivityLog, TabView
from questions.services import get_user_themes, has_new_questions, has_new_themes


def unread_notifications(request):
    if not request.user.is_authenticated:
        return {}

    # --- Пользователи и группы ---
    last_view_users = TabView.objects.filter(
        user=request.user,
        logical_question=None,
        tab_type='user_list'
    ).first()
    last_viewed_users = last_view_users.viewed_at if last_view_users else None

    new_users_activities = ActivityLog.objects.filter(
        entity_type__in=['user', 'group']
    ).exclude(user=request.user)

    if last_viewed_users:
        new_users_activities = new_users_activities.filter(created_at__gt=last_viewed_users)

    new_users_count = new_users_activities.count()

    # --- Вопросы и темы ---
    available_themes = get_user_themes(request.user)
    if available_themes.exists():
        new_questions_exist = has_new_questions(request.user)
        new_themes_exist = has_new_themes(request.user)
    else:
        new_questions_exist = False
        new_themes_exist = False

    # История
    last_view_hist = TabView.objects.filter(user=request.user, logical_question=None,
                                            tab_type='question_history').first()
    last_viewed_hist = last_view_hist.viewed_at if last_view_hist else None
    new_history = ActivityLog.objects.filter(entity_type__in=['question', 'theme']).exclude(user=request.user)
    available_themes = get_user_themes(request.user)
    if not request.user.is_superuser:
        new_history = new_history.filter(theme__in=available_themes)
    if last_viewed_hist:
        new_history = new_history.filter(created_at__gt=last_viewed_hist)
    history_has_new = new_history.exists()

    new_questions_count = new_questions_exist or new_themes_exist or history_has_new

    return {
        'new_users_count': new_users_count,
        'new_questions_exist': new_questions_exist,
        'new_themes_exist': new_themes_exist,
        'history_has_new': history_has_new,
        'new_questions_count': new_questions_count,
    }


def section_context(request):
    view_name = request.resolver_match.view_name if request.resolver_match else ''
    return {
        'is_questions_section': view_name.startswith('questions:'),
        'is_users_section': view_name.startswith('users:'),
        'is_description_section': view_name.startswith('description:'),
    }