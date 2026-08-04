from django.db import models
from core.enums import ACType, QType
from core.field_validators.validators import validate_file_size, validate_image
from config import settings



# Модель тем вопросов
class Themes(models.Model):
    name = models.CharField(max_length=200, verbose_name="Название Темы")
    description = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['name']
        verbose_name = "Тема"
        verbose_name_plural = "Темы"

    def __str__(self):
        return f'{self.name}'


# ============================================
# 1. Абстрактный базовый класс для вопросов с общей логикой
# ============================================

class BaseQuestion(models.Model):
    """Абстрактный базовый класс для всех типов вопросов."""

    # Основное содержание
    question = models.TextField(verbose_name='Текст вопроса')
    # Имя темы связано с классом Theme
    theme = models.ForeignKey('Themes', on_delete=models.CASCADE, verbose_name='Тема')
    ac_type = models.CharField(max_length=10, choices=ACType.choices, verbose_name='Тип ВС')

    # Дополнительные поля

    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    q_kind = models.CharField(
        max_length=20,
        choices=QType.choices,
        default=QType.SINGLE,
        verbose_name='Один или Несколько правильных ответов'
    )
    q_weight = models.FloatField(
        default=1.0,
        verbose_name='Вес вопроса'
    )
    is_time_limited = models.BooleanField(
        default=False,
        verbose_name='С ограничением по времени'
    )

    # Изображения
    question_img = models.ImageField(
        upload_to='questions/img/',
        validators=[validate_image],
        blank=True,
        null=True,
        verbose_name='Картинка к вопросу'
    )
    comment_img = models.ImageField(
        upload_to='questions/comments/',
        validators=[validate_image],
        blank=True,
        null=True,
        verbose_name='Картинка пояснения'
    )
    comment_text = models.TextField(
        blank=True,
        null=True,
        verbose_name='Текст пояснения'
    )

    def get_answers(self):
        """Получить ответы для вопроса (будет переопределено)."""
        raise NotImplementedError

    class Meta:
        abstract = True


    def __str__(self):
        try:
            return f'{self.theme.name}: {self.question[:50]}...'
        except Exception:
            return f'Question: {self.question[:50] if self.question else "?"}...'




# Модель вопроса
class Question(BaseQuestion):
    """Оригинальный вопрос-шаблон. Версионируется, редактируется."""

    is_published = models.BooleanField(default=False,
                                       verbose_name='Опубликован',
                                       help_text='Доступен для тестов')

    published_at =  models.DateTimeField(null=True, blank=True, verbose_name='Дата публикации')

    is_archived = models.BooleanField(
        default=False,
        verbose_name='Архивный',
        help_text='Заменён на новую версию'
    )

    previous_version = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='archived_versions',
        verbose_name='Предыдущая версия'
    )


    # Кто создал вопрос
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_questions',
        verbose_name='Создатель'
    )

    def delete(self, *args, **kwargs):
        """При удалении вопроса удаляем и его предыдущую версию."""
        if self.previous_version:
            self.previous_version.delete()
        super().delete(*args, **kwargs)

    def get_answers(self):
        """Получить ответы для оригинального вопроса."""
        return self.answers.all()

    class Meta:
        ordering = ['theme__name', 'question']
        verbose_name = "Вопрос"
        verbose_name_plural = "Вопросы"



class QuestionParaphrase(BaseQuestion):
    """Перефразированный вопрос для конкретного теста."""

    original_question = models.ForeignKey(Question,
                                         verbose_name="Original question",
                                         on_delete=models.CASCADE,
                                         related_name='paraphrases',
                                         help_text='Это перефразированный вопрос')

    is_published = models.BooleanField(
        default=False,
        verbose_name='Опубликован',
        help_text='Доступен для использования в тестах'
    )

    usage_count = models.PositiveIntegerField(
        default=0,
        verbose_name='Количество использований'
    )

    # Кто создал перефразировку
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_paraphrases',
        verbose_name='Создатель'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Перефразированный вопрос"
        verbose_name_plural = "Перефразированные вопросы"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['original_question', 'is_published']),
        ]

    def get_answers(self):
        """Получить ответы из оригинального вопроса."""
        return self.original_question.get_answers()

    def __str__(self):
        return f'Перефразирование: {self.question[:50]}...'


class QuestionDraft(BaseQuestion):
    """Черновик вопроса. Существует параллельно с активным вопросом."""

    # Связь с оригинальным вопросом
    original_question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name='drafts',
        verbose_name='Оригинальный вопрос'
    )

    # Кто создал черновик
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_drafts',
        verbose_name='Создатель черновика'
    )

    # Примечание: флаги is_published, is_draft, is_archived НЕ НУЖНЫ
    # Это черновик по определению

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Черновик вопроса"
        verbose_name_plural = "Черновики вопросов"
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['original_question']),
            models.Index(fields=['created_by', 'updated_at']),
            models.Index(fields=['-created_at']),  # для быстрой сортировки
        ]

    def get_answers(self):
        """Получить ответы для оригинального вопроса."""
        return self.answers.all()

    def __str__(self):
        return f'Черновик: {self.question[:50]}...'


# Модель ответа
class Answer(models.Model):
    answer = models.CharField(max_length=1000,
                              verbose_name="Формулировка ответа"
                              )

    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='answers'
    )

    question_draft = models.ForeignKey(
        QuestionDraft,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='answers'
    )

    is_correct = models.BooleanField(default=False,
                                     verbose_name='Правильный Ответ на вопрос'
                                     )

    answer_order = models.PositiveIntegerField(default=0,
                                               verbose_name='Порядок отображения'
                                               )

    def save(self, *args, **kwargs):
        if not self.question_id and not self.question_draft_id:
            raise ValueError("Answer должен быть привязан либо к Question, либо к QuestionDraft")
        if self.question_id and self.question_draft_id:
            raise ValueError("Answer не может быть привязан одновременно к Question и QuestionDraft")
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['question', 'answer_order']
        verbose_name = "Ответ"
        verbose_name_plural = "Ответы"

    def __str__(self):
        try:
            if self.question:
                return f'{self.question.question[:50]}, {self.answer[:50]}...'
            elif self.question_draft:
                return f'{self.question_draft.question[:50]}, {self.answer[:50]}...'
        except Exception:
            pass
        return f'{self.answer[:50]}...'