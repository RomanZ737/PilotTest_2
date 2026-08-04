from django.db import models
from config import settings


class DraftView(models.Model):
    """Фиксирует просмотр черновика пользователем."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='draft_views'
    )
    draft = models.ForeignKey(
        'questions.QuestionDraft',
        on_delete=models.CASCADE,
        related_name='views'
    )
    viewed_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'draft']
        verbose_name = "Просмотр черновика"
        verbose_name_plural = "Просмотры черновиков"
        indexes = [
            models.Index(fields=['user', 'viewed_at']),
        ]

    def __str__(self):
        return f'{self.user} просмотрел {self.draft} в {self.viewed_at}'


class QuestionHistory(models.Model):
    """Запись о действии с вопросом."""

    ENTITY_TYPES = [
        ('question', 'Активный вопрос'),
        ('draft', 'Черновик'),
        ('paraphrase', 'Перефразировка'),
    ]

    logical_question = models.ForeignKey(
        'questions.Question',
        on_delete=models.CASCADE,
        related_name='history'
    )

    entity_type = models.CharField(
        max_length=20,
        choices=ENTITY_TYPES,
        verbose_name='Тип сущности',
        help_text='С каким вопросом связана запись истории (Черновик, основной вопрос, перефраз)'
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='question_history'
    )

    user_name = models.CharField(
        max_length=150,
        blank=True,
        verbose_name='Имя пользователя',
        help_text='Сохраняется на момент создания записи. Используется, если пользователь удалён.'
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата действия')

    class Meta:
        verbose_name = "История вопроса"
        verbose_name_plural = "Истории вопросов"
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user} - {self.logical_question} - {self.created_at}'


class Action(models.Model):
    """Конкретное действие в истории вопроса."""

    ACTION_TYPES = [
        ('created', 'Создан'),
        ('updated_field', 'Изменение поля'),
        ('published', 'Публикация'),
        ('unpublished', 'Снятие с публикации'),
        ('archived', 'Архивирование'),
        ('restored', 'Восстановление из архива'),
        ('deleted', 'Удалён')
    ]

    history = models.ForeignKey(
        QuestionHistory,
        on_delete=models.CASCADE,
        related_name='actions'
    )
    action_type = models.CharField(max_length=20, choices=ACTION_TYPES)
    field_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='Для типа "updated_field"'
    )
    old_value = models.TextField(blank=True, null=True)
    new_value = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Действие"
        verbose_name_plural = "Действия"
        ordering = ['created_at']

    def __str__(self):
        return f'{self.get_action_type_display()} - {self.history.logical_question}'


class Comment(models.Model):
    """Комментарий к действию."""

    history = models.ForeignKey(
        QuestionHistory,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='question_comments'
    )
    user_name = models.CharField(
        max_length=150,
        blank=True,
        verbose_name='Имя пользователя',
        help_text='Сохраняется на момент создания. Используется, если пользователь удалён.'
    )
    text = models.TextField(verbose_name='Текст комментария')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Комментарий"
        verbose_name_plural = "Комментарии"
        ordering = ['created_at']

    # ... методы get_cleaned_text без изменений ...

    def __str__(self):
        name = self.user.get_full_name() if self.user else (self.user_name or 'Удалён')
        return f'{name}: {self.text[:50]}...'