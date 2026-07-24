from django.utils.crypto import get_random_string
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse

def generate_verification_token():
    """Генерирует уникальный токен для подтверждения email."""
    return get_random_string(length=64)

def send_verification_email(user, request):
    """Отправляет письмо со ссылкой для подтверждения."""
    token = user.email_verification_token

    verification_url = request.build_absolute_uri(
        reverse('users:verify_email', kwargs={'token': token})
    )
    subject = 'Подтверждение email для SPAM SERVICE'
    message = f"""
    Здравствуйте! Для завершения регистрации  и подтверждения email перейдите по ссылке: 
    {verification_url}



    С уважением,
    SPAM SERVICE
    """
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [user.email]
    send_mail(subject, message, from_email, recipient_list, fail_silently=False)