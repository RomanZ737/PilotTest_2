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

    # Тип сущности, в которой произошло изменение
    entity_type = models.CharField(
        max_length=20,
        choices=ENTITY_TYPES,
        verbose_name='Тип сущности',
        help_text='С каким вопросом связана запись истории (Черновик, основной вопрос, перефраз)'
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='question_history'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "История вопроса"
        verbose_name_plural = "Истории вопросов"
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user} - {self.logical_question} - {self.created_at}'


class Action(models.Model):
    """Конкретное действие в истории вопроса."""

    ACTION_TYPES = [
        ('created', 'Создание вопроса'),
        ('updated_field', 'Изменение поля'),
        ('published', 'Публикация'),
        ('unpublished', 'Снятие с публикации'),
        ('archived', 'Архивирование'),
        ('restored', 'Восстановление из архива'),
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
        on_delete=models.CASCADE,
        related_name='question_comments'
    )
    text = models.TextField(verbose_name='Текст комментария')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Комментарий"
        verbose_name_plural = "Комментарии"
        ordering = ['created_at']

    def get_cleaned_text(self):
        """Возвращает текст без пробелов и табуляции в начале каждой строки."""
        lines = self.text.splitlines()
        cleaned_lines = []
        for line in lines:
            # Удаляем все пробельные символы в начале строки
            cleaned_line = line.lstrip(' \t\r\n')
            cleaned_lines.append(cleaned_line)
        return '\n'.join(cleaned_lines)

    def get_cleaned_text_with_br(self):
        """Возвращает текст с <br> вместо переносов строк."""
        return self.get_cleaned_text().replace('\n', '<br>')

    def __str__(self):
        return f'{self.user}: {self.text[:50]}...'