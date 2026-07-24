from django.utils import timezone
from .models import Mailing
from django.core.mail import send_mail
from config import settings
from history.models import History


def send_mailing(mailing):
    """
    Отправляет письма всем получателям рассылки и сохраняет историю.
    Использует bulk_create для массовой вставки записей в БД.
    """
    from history.models import History  # импорт внутри, чтобы избежать циклических зависимостей
    from django.core.mail import send_mail
    from django.conf import settings

    subject = mailing.message.subject
    content = mailing.message.content
    from_email = settings.DEFAULT_FROM_EMAIL

    # Список для хранения объектов History (ещё не сохранённых)
    history_objects = []
    # Список для результатов (чтобы вернуть для отображения)
    results = []

    for recipient in mailing.recipients.all():
        try:
            send_mail(subject, content, from_email, [recipient.email])
            status = 'success'
            response = 'Успешно отправлено'
        except Exception as e:
            status = 'failed'
            response = str(e)

        # Создаём объект History, но не сохраняем в БД (без .save())
        history_obj = History(
            mailing=mailing,
            recipient=recipient,
            status=status,
            server_response=response
        )
        history_objects.append(history_obj)

        results.append({
            'recipient': recipient,
            'status': status,
            'response': response,
        })

    if history_objects:
        History.objects.bulk_create(history_objects)

    return results


def update_mailing_status(mailing):
    """
    Обновляет статус рассылки, если она не приостановлена.
    """
    # Если рассылка приостановлена – не меняем статус
    if mailing.status == 'paused':
        return False

    now = timezone.now()
    if mailing.start_time and mailing.end_time:
        if now < mailing.start_time:
            new_status = 'created'
        elif mailing.start_time <= now <= mailing.end_time:
            new_status = 'started'
        else:
            new_status = 'finished'

        if mailing.status != new_status:
            Mailing.objects.filter(pk=mailing.pk).update(status=new_status)
            mailing.status = new_status
            return True
    return False


def update_all_mailing_statuses(queryset=None):
    """
    Обновляет статусы для всех (или переданных) рассылок.
    Выполняет массовое обновление тремя запросами.
    """

    if queryset is None:
        queryset = Mailing.objects.all()

    now = timezone.now()


    queryset.filter(
        start_time__gt=now
    ).exclude(
        status='created'
    ).exclude(
        status='paused'
    ).update(status='created')


    queryset.filter(
        start_time__lte=now,
        end_time__gte=now
    ).exclude(
        status='started'
    ).exclude(
        status='paused'
    ).update(status='started')


    queryset.filter(
        end_time__lt=now
    ).exclude(
        status='finished'
    ).exclude(
        status='paused'
    ).update(status='finished')