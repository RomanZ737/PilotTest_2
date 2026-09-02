from django.db.models import OuterRef, Exists, Subquery
from questions.models import Themes, Question, QuestionDraft, QuestionParaphrase
from users.models import UserTheme
from history.models import TabView
from django.utils import timezone


def reset_user_views(user):
    """Отмечает все доступные вопросы и темы как просмотренные (при добавлении пользователя)"""
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

    for theme in themes:
        TabView.objects.update_or_create(
            user=user,
            theme=theme,
            logical_question=None,
            tab_type='theme',
            defaults={'viewed_at': now}
        )


def get_user_themes(user):
    if not user.is_authenticated:
        return Themes.objects.none()
    if user.is_superuser or user.groups.filter(name='Администраторы').exists():
        return Themes.objects.all()
    if user.groups.filter(name__in=['Редактор', 'Супер Редактор']).exists():
        theme_ids = UserTheme.objects.filter(user=user).values_list('theme_id', flat=True)
        return Themes.objects.filter(id__in=theme_ids)
    return Themes.objects.none()


def has_new_questions(user):
    available_themes = get_user_themes(user)
    if not available_themes.exists():
        return False

    # ID просмотренных вопросов (основных)
    viewed_question_ids = set(
        TabView.objects.filter(user=user, tab_type='question').values_list('logical_question_id', flat=True)
    )

    # ID просмотренных черновиков
    viewed_draft_ids = set(
        TabView.objects.filter(user=user, tab_type='draft').values_list('logical_question_id', flat=True)
    )

    # ID просмотренных перефразов
    viewed_paraphrase_ids = set(
        TabView.objects.filter(user=user, tab_type='paraphrase').values_list('logical_question_id', flat=True)
    )

    # Проверяем основные вопросы
    questions = Question.objects.filter(
        theme__in=available_themes,
        is_archived=False
    ).only('id', 'updated_at')

    for q in questions:
        if q.id not in viewed_question_ids:
            return True

    # Проверяем черновики
    drafts = QuestionDraft.objects.filter(
        original_question__theme__in=available_themes,
        original_question__is_archived=False
    ).only('id', 'original_question_id', 'updated_at')

    for d in drafts:
        if d.original_question_id not in viewed_draft_ids:
            return True

    # Проверяем перефразы
    paraphrases = QuestionParaphrase.objects.filter(
        original_question__theme__in=available_themes,
        original_question__is_archived=False
    ).only('id', 'original_question_id', 'updated_at')

    for p in paraphrases:
        if p.original_question_id not in viewed_paraphrase_ids:
            return True

    return False


def get_new_questions_queryset(user, queryset):
    # Получаем ID просмотренных вопросов, черновиков, перефразов
    viewed_question_ids = set(
        TabView.objects.filter(user=user, tab_type='question').values_list('logical_question_id', flat=True)
    )
    viewed_draft_ids = set(
        TabView.objects.filter(user=user, tab_type='draft').values_list('logical_question_id', flat=True)
    )
    viewed_paraphrase_ids = set(
        TabView.objects.filter(user=user, tab_type='paraphrase').values_list('logical_question_id', flat=True)
    )

    # ID вопросов, у которых нет просмотра основного вопроса
    new_question_ids = set(
        Question.objects.filter(is_archived=False)
        .exclude(pk__in=viewed_question_ids)
        .values_list('pk', flat=True)
    )

    # ID вопросов с новыми черновиками
    new_draft_ids = set(
        QuestionDraft.objects.filter(
            original_question__is_archived=False
        )
        .exclude(original_question_id__in=viewed_draft_ids)
        .values_list('original_question_id', flat=True)
    )

    # ID вопросов с новыми перефразами
    new_paraphrase_ids = set(
        QuestionParaphrase.objects.filter(
            original_question__is_archived=False
        )
        .exclude(original_question_id__in=viewed_paraphrase_ids)
        .values_list('original_question_id', flat=True)
    )

    all_new_ids = new_question_ids | new_draft_ids | new_paraphrase_ids

    return queryset.filter(pk__in=all_new_ids)

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
    themes = get_user_themes(user)
    if not themes.exists():
        return

    now = timezone.now()
    questions = Question.objects.filter(
        theme__in=themes,
        is_archived=False
    )

    for q in questions:
        # Сбрасываем просмотр основного вопроса
        TabView.objects.update_or_create(
            user=user,
            logical_question=q,
            tab_type='question',
            defaults={'viewed_at': now}
        )

        # Сбрасываем просмотр черновика, если он есть
        draft = q.drafts.order_by('-updated_at').first()
        if draft:
            TabView.objects.update_or_create(
                user=user,
                logical_question=q,
                tab_type='draft',
                defaults={'viewed_at': now}
            )

        # Сбрасываем просмотр перефраза, если он есть
        paraphrase = q.paraphrases.first()
        if paraphrase:
            TabView.objects.update_or_create(
                user=user,
                logical_question=q,
                tab_type='paraphrase',
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