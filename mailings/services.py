from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from .models import Attempt


class MailingSendError(Exception):
    """Ошибка отправки рассылки."""


def send_mailing(mailing):
    """
    Отправляет рассылку всем получателям.
    Возвращает список созданных Attempt (batch).
    Бросает MailingSendError, если сейчас не окно рассылки.
    """
    now = timezone.now()
    if not (mailing.start_time <= now <= mailing.end_time):
        raise MailingSendError(
            f"Сейчас отправка невозможна: текущее время вне диапазона "
            f"{mailing.start_time:%d.%m.%Y %H:%M} — {mailing.end_time:%d.%m.%Y %H:%M}."
        )

    recipients = list(mailing.recipients.all())
    if not recipients:
        raise MailingSendError("У рассылки нет получателей.")

    attempts_to_create = []
    for recipient in recipients:
        try:
            sent = send_mail(
                subject=mailing.message.subject,
                message=mailing.message.body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient.email],
                fail_silently=False,
            )
            status = Attempt.STATUS_SUCCESS if sent else Attempt.STATUS_FAILED
            response = f"Отправлено на {recipient.email}"
        except Exception as exc:
            status = Attempt.STATUS_FAILED
            response = f"{type(exc).__name__}: {exc}"

        attempts_to_create.append(
            Attempt(mailing=mailing, status=status, server_response=response)
        )

    # batch-создание записей о попытках
    Attempt.objects.bulk_create(attempts_to_create)
    return attempts_to_create
