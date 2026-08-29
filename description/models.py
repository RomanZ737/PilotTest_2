from django.db import models


class DescriptionPage(models.Model):
    """Страница описания раздела."""

    slug = models.SlugField(unique=True, verbose_name='Идентификатор раздела')
    title = models.CharField(max_length=200, verbose_name='Заголовок')
    content = models.TextField(blank=True, verbose_name='Содержание')

    class Meta:
        verbose_name = 'Страница описания'
        verbose_name_plural = 'Страницы описания'
        ordering = ['id']

    def __str__(self):
        return self.title
