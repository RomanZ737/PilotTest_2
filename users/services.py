from django.utils.crypto import get_random_string
from django.urls import reverse
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string


def generate_verification_token():
    """Генерирует уникальный токен для подтверждения email."""
    return get_random_string(length=64)

def send_verification_email(user, request):
    """Отправляет письмо со ссылкой для подтверждения email."""
    token = user.email_verification_token

    verification_url = request.build_absolute_uri(
        reverse('users:verify_email', kwargs={'token': token})
    )

    context = {
        'verification_url': verification_url,
    }

    html_content = render_to_string('users/email/verification_email.html', context)

    subject = 'Подтверждение email для Pilot Test'
    from_email = settings.DEFAULT_FROM_EMAIL

    msg = EmailMultiAlternatives(
        subject=subject,
        body=f'Для подтверждения email перейдите по ссылке:\n\n{verification_url}',
        from_email=from_email,
        to=[user.email],
    )
    msg.attach_alternative(html_content, 'text/html')
    msg.send()





def send_welcome_email(user, password):
    """Отправка приветственного письма с учётными данными."""

    context = {
        'first_name': user.first_name,
        'middle_name': user.middle_name or '',
        'email': user.email,
        'password': password,
        'site_url': settings.SITE_URL or 'http://127.0.0.1:8000',
    }

    html_content = render_to_string('users/email/welcome_email.html', context)

    subject = 'Учётная запись Pilot Test'
    from_email = settings.DEFAULT_FROM_EMAIL

    msg = EmailMultiAlternatives(
        subject=subject,
        body=f'Ваш логин: {user.email}\nВременный пароль: {password}\n\n{settings.SITE_URL}',
        from_email=from_email,
        to=[user.email],
    )
    msg.attach_alternative(html_content, 'text/html')
    msg.send()