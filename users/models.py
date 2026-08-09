from django.contrib.auth.models import AbstractUser
from django.db import models
from core.enums import Position, ACType


class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    is_email_verified = models.BooleanField(default=False)
    email_verification_token = models.CharField(max_length=100, blank=True, null=True)
    middle_name = models.CharField(max_length=30, blank=True, null=True)
    position = models.CharField(max_length=10, choices=Position.choices, blank=True, null=True)
    ac_type = models.CharField(max_length=10, choices=ACType.choices, blank=True)



    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email

    class Meta:
        permissions = (
            ("can_deactivate_user", "Can deactivate any user"),
        )


class GroupsDescription(models.Model):
    group = models.OneToOneField(
        'auth.Group',
        on_delete=models.CASCADE,
        related_name='description'
    )
    description = models.CharField(max_length=200, verbose_name='Описание группы')
    is_fixed = models.BooleanField(
        default=False,
        verbose_name='Фиксированная группа',
        help_text='Фиксированные группы нельзя удалить'
    )

    def __str__(self):
        return f'{self.group.name} — {self.description}'


class UserTheme(models.Model):
    """Связь пользователя с темами вопросов (для редакторов и супер редакторов)."""

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='user_themes',
        verbose_name='Пользователь'
    )
    theme = models.ForeignKey(
        'questions.Themes',
        on_delete=models.CASCADE,
        related_name='assigned_users',
        verbose_name='Тема'
    )

    class Meta:
        unique_together = ['user', 'theme']
        verbose_name = 'Тема пользователя'
        verbose_name_plural = 'Темы пользователей'

    def __str__(self):
        return f'{self.user.email} → {self.theme.name}'