from django.db import models
from core.enums import ACType, QType



# Модель тем вопросов
class Themes(models.Model):
    name = models.CharField(max_length=200, verbose_name="Название Темы")
    description = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['name']
        verbose_name = "Тема"
        verbose_name_plural = "Темы"

    def __str__(self):
        return f'{self.name}, {self.description}'


# ============================================
# 1. Абстрактный базовый класс для вопросов с общей логикой
# ============================================

class BaseQuestion(models.Model):
    """Абстрактный базовый класс для всех типов вопросов."""

    # Основное содержание
    question = models.TextField(verbose_name='Текст вопроса')
    # Имя темы связано с классом Theme
    theme = models.ForeignKey('Themes', on_delete=models.PROTECT, verbose_name='Тема')
    ac_type = models.CharField(max_length=10, choices=ACType.choices, verbose_name='Тип ВС')

    # Дополнительные поля
    is_published = models.BooleanField(default=False, verbose_name='Опубликован')
    published_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    q_kind = models.BooleanField(
        default=False,
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
        blank=True,
        null=True,
        verbose_name='Картинка к вопросу'
    )
    comment_img = models.ImageField(
        upload_to='comments/',
        blank=True,
        null=True,
        verbose_name='Картинка пояснения'
    )
    comment_text = models.TextField(
        blank=True,
        null=True,
        verbose_name='Текст пояснения'
    )

    class Meta:
        abstract = True

    def __str__(self):
        return f'{self.theme.name}: {self.question[:50]}...'

    def get_answers(self):
        """Получить ответы для вопроса (будет переопределено)."""
        raise NotImplementedError


# Модель вопроса
class Question(BaseQuestion):
    """Оригинальный вопрос-шаблон. Версионируется, редактируется."""

    previous_version = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='previous_versions',
        verbose_name='Предыдущая версия'
    )
    is_draft = models.BooleanField(default=True, verbose_name='Черновик')

    is_paraphrased = models.BooleanField(default=False,
                                         verbose_name='Does the question paraphrased',
                                         help_text='Перефразирован ли вопрос')

    def get_answers(self):
        """Получить ответы для оригинального вопроса."""
        return self.answers.all()

    class Meta:
        ordering = ['theme__name', 'question']
        verbose_name = "Вопрос"
        verbose_name_plural = "Вопросы"



class QuestionSnapshot(BaseQuestion):
    """Перефразированный вопрос для конкретного теста."""
    original_question = models.ForeignKey(Question,
                                         verbose_name="Original question",
                                         on_delete=models.CASCADE,
                                         help_text='Это перефразированный вопрос')

    def get_answers(self):
        """Получить ответы из оригинального вопроса."""
        return self.original_question.get_answers()

    class Meta:
        ordering = ['theme__name', 'question']
        verbose_name = "Перефразированный Вопрос"
        verbose_name_plural = "Перефразированные вопросы Вопросы"




# Модель ответа
class Answer(models.Model):
    answer = models.CharField(max_length=200, verbose_name="Формулировка ответа")
    question = models.ForeignKey(Question, related_name='answers', on_delete=models.CASCADE)
    is_correct = models.BooleanField(default=False, verbose_name='Правильный Ответ на вопрос')

    class Meta:
        ordering = ['question']
        verbose_name = "Ответ"
        verbose_name_plural = "Ответы"


    def __str__(self):
        return f'{self.question.question[:50]}, {self.answer[:50]}...'