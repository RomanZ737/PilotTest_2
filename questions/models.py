from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from users.models import CustomUser
from message.models import Message
from recipient.models import Recipient


# Создаём списки choices с русскими названиями
MAILING_STATUS = [
    ('created', 'Создана'),
    ('started', 'Запущена'),
    ('finished', 'Завершена'),
    ('paused', 'Приостановлена'),
]







class Mailing(models.Model):
    start_time = models.DateTimeField(verbose_name='start_of_mailing', help_text='Дата и время начала рассылки')
    end_time = models.DateTimeField(verbose_name='end_of_mailing', help_text='Дата и время окончания рассылки')
    status = models.CharField(max_length=20, choices=MAILING_STATUS, default='created')
    message = models.ForeignKey(Message, on_delete=models.CASCADE)
    recipients = models.ManyToManyField(Recipient)
    owner = models.ForeignKey(CustomUser, on_delete=models.CASCADE, default=1)

    def __str__(self):
        return (f'Начало: {self.start_time} Окончание: {self.end_time}'
                f' Тема: {self.message.subject} Статус: {self.get_status_display()}')

    class Meta:
        verbose_name = 'Рассылка'
        verbose_name_plural = 'Рассылки'
        ordering = ['-start_time']

    def clean(self):
        if self.start_time and self.start_time < timezone.now():
            raise ValidationError({
                'start_time': 'Начало рассылки не может быть в прошлом.'
            })
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValidationError({
                'end_time': 'Окончание должно быть позже начала.'
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)