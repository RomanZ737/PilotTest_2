from questions.models import Themes, Question
from users.models import UserTheme
from django.db.models import Q, OuterRef, Exists, Subquery
from history.models import TabView
from django.utils import timezone


def reset_user_views(user):
    """Отмечает все доступные вопросы и темы как просмотренные (при добавлении пользователя)"""
    themes = get_user_themes(user)
    if not themes.exists():
        return

    now = timezone.now()

    # Все вопросы в доступных темах
    questions = Question.objects.filter(
        theme__in=themes,
        is_archived=False
    )
    for question in questions:
        TabView.objects.update_or_create(
            user=user,
            logical_question=question,
            tab_type='question',
            defaults={'viewed_at': now}
        )

    # Темы: для каждой темы берём последний вопрос и создаём TabView
    for theme in themes:
        TabView.objects.update_or_create(
            user=user,
            theme=theme,
            logical_question=None,
            tab_type='theme',
            defaults={'viewed_at': now}
        )


def get_user_themes(user):
    """Возвращает queryset тем, доступных пользователю.

    - Суперпользователь/Администраторы: все темы
    - Редакторы/Супер редакторы: только назначенные
    - Остальные: None (нет доступа к базе вопросов)
    """
    if not user.is_authenticated:
        return Themes.objects.none()

    if user.is_superuser or user.groups.filter(name='Администраторы').exists():
        return Themes.objects.all()

    if user.groups.filter(name__in=['Редактор', 'Супер Редактор']).exists():
        theme_ids = UserTheme.objects.filter(user=user).values_list('theme_id', flat=True)
        return Themes.objects.filter(id__in=theme_ids)

    return Themes.objects.none()


def get_new_questions_queryset(user, queryset):
    """
    Возвращает queryset вопросов, которые пользователь ещё не просмотрел.
    """
    last_view_subquery = TabView.objects.filter(
        user=user,
        logical_question=OuterRef('pk'),
        tab_type='question',
        viewed_at__gte=OuterRef('updated_at')
    )
    queryset = queryset.filter(~Exists(last_view_subquery))
    return queryset


def has_new_questions(user):
    """Возвращает True, если есть хотя бы один новый вопрос для пользователя."""

    available_themes = get_user_themes(user)
    if not available_themes.exists():
        return False
    base_qs = Question.objects.filter(
        theme__in=available_themes,
        is_archived=False
    )
    last_view_subquery = TabView.objects.filter(
        user=user,
        logical_question=OuterRef('pk'),
        tab_type='question',
        viewed_at__gte=OuterRef('updated_at')
    )
    return base_qs.filter(~Exists(last_view_subquery)).exists()


def has_new_themes(user):
    """Проверяет, есть ли новые темы для пользователя."""
    available_themes = get_user_themes(user)
    if not available_themes.exists():
        return False

    for theme in available_themes:
        last_view = TabView.objects.filter(
            user=user,
            theme=theme,
            tab_type='theme'
        ).first()
        if not last_view or last_view.viewed_at < theme.updated_at:
            return True
    return False


def reset_question_views(user):
    """Отмечает все доступные вопросы как просмотренные."""
    themes = get_user_themes(user)
    if not themes.exists():
        return

    now = timezone.now()
    questions = Question.objects.filter(
        theme__in=themes,
        is_archived=False
    )
    for question in questions:
        TabView.objects.update_or_create(
            user=user,
            logical_question=question,
            tab_type='question',
            defaults={'viewed_at': now}
        )


def reset_theme_views(user):
    themes = get_user_themes(user)
    now = timezone.now()
    for theme in themes:
        TabView.objects.update_or_create(
            user=user,
            theme=theme,
            logical_question=None,
            tab_type='theme',
            defaults={'viewed_at': now}
        )