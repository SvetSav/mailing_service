from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from clients.models import Recipient

from .forms import MailingForm
from .models import Attempt, Mailing, Message
from .services import MailingSendError, send_mailing

User = get_user_model()


class MailingModelTests(TestCase):
    """Тесты для модели Mailing (динамический статус)."""

    def setUp(self):
        self.user = User.objects.create_user(email="test@test.com", password="123")
        self.msg = Message.objects.create(subject="Test", body="Body", owner=self.user)
        self.now = timezone.now()

    def test_status_created(self):
        """Если start_time в будущем, статус 'Создана'."""
        mailing = Mailing.objects.create(
            start_time=self.now + timedelta(hours=1),
            end_time=self.now + timedelta(hours=2),
            message=self.msg,
            owner=self.user,
        )
        self.assertEqual(mailing.get_calculated_status(), Mailing.STATUS_CREATED)

    def test_status_started(self):
        """Если сейчас между start и end, статус 'Запущена'."""
        mailing = Mailing.objects.create(
            start_time=self.now - timedelta(hours=1),
            end_time=self.now + timedelta(hours=1),
            message=self.msg,
            owner=self.user,
        )
        self.assertEqual(mailing.get_calculated_status(), Mailing.STATUS_STARTED)

    def test_status_finished(self):
        """Если end_time в прошлом, статус 'Завершена'."""
        mailing = Mailing.objects.create(
            start_time=self.now - timedelta(hours=2),
            end_time=self.now - timedelta(hours=1),
            message=self.msg,
            owner=self.user,
        )
        self.assertEqual(mailing.get_calculated_status(), Mailing.STATUS_FINISHED)

    def test_update_status_saves_to_db(self):
        """Метод update_status должен сохранять новый статус в БД."""
        mailing = Mailing.objects.create(
            start_time=self.now - timedelta(hours=1),
            end_time=self.now + timedelta(hours=1),
            message=self.msg,
            owner=self.user,
            status=Mailing.STATUS_CREATED,  # Изначально неверный статус
        )
        mailing.update_status()
        mailing.refresh_from_db()
        self.assertEqual(mailing.status, Mailing.STATUS_STARTED)


class MailingFormTests(TestCase):
    """Тесты валидации формы рассылки."""

    def setUp(self):
        self.user = User.objects.create_user(email="test@test.com", password="123")
        self.msg = Message.objects.create(subject="Test", body="Body", owner=self.user)
        self.recipient = Recipient.objects.create(
            email="a@a.com", full_name="A", owner=self.user
        )

    def test_start_time_in_past(self):
        """Валидация: дата начала не может быть в прошлом."""
        now = timezone.now()
        data = {
            "start_time": (now - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M"),
            "end_time": (now + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M"),
            "message": self.msg.id,
            "recipients": [self.recipient.id],
        }
        form = MailingForm(data=data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn("Дата начала не может быть в прошлом", form.non_field_errors()[0])

    def test_start_time_greater_than_end_time(self):
        """Валидация: дата начала должна быть раньше даты окончания."""
        now = timezone.now()
        data = {
            "start_time": (now + timedelta(days=2)).strftime("%Y-%m-%dT%H:%M"),
            "end_time": (now + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M"),
            "message": self.msg.id,
            "recipients": [self.recipient.id],
        }
        form = MailingForm(data=data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn(
            "Дата начала должна быть раньше даты окончания", form.non_field_errors()[0]
        )


@patch("mailings.services.send_mail")
class MailingServiceTests(TestCase):
    """Тесты сервиса отправки send_mailing."""

    def setUp(self):
        self.user = User.objects.create_user(email="test@test.com", password="123")
        self.msg = Message.objects.create(
            subject="Test Subject", body="Body", owner=self.user
        )
        self.recipient1 = Recipient.objects.create(
            email="r1@test.com", full_name="R1", owner=self.user
        )
        self.recipient2 = Recipient.objects.create(
            email="r2@test.com", full_name="R2", owner=self.user
        )
        self.now = timezone.now()

    def test_send_outside_window(self, mock_send_mail):
        """Ошибка, если текущее время вне окна рассылки."""
        mailing = Mailing.objects.create(
            start_time=self.now + timedelta(hours=1),
            end_time=self.now + timedelta(hours=2),
            message=self.msg,
            owner=self.user,
        )
        with self.assertRaises(MailingSendError):
            send_mailing(mailing)
        mock_send_mail.assert_not_called()

    def test_send_without_recipients(self, mock_send_mail):
        """Ошибка, если у рассылки нет получателей."""
        mailing = Mailing.objects.create(
            start_time=self.now - timedelta(hours=1),
            end_time=self.now + timedelta(hours=1),
            message=self.msg,
            owner=self.user,
        )
        with self.assertRaises(MailingSendError):
            send_mailing(mailing)
        mock_send_mail.assert_not_called()

    def test_send_success_and_batch_creation(self, mock_send_mail):
        """Успешная отправка создает попытки через batch (bulk_create)."""
        mailing = Mailing.objects.create(
            start_time=self.now - timedelta(hours=1),
            end_time=self.now + timedelta(hours=1),
            message=self.msg,
            owner=self.user,
        )
        mailing.recipients.add(self.recipient1, self.recipient2)

        mock_send_mail.return_value = 1  # Имитация успешной отправки

        attempts = send_mailing(mailing)

        # Проверяем, что send_mail вызван 2 раза (для 2 получателей)
        self.assertEqual(mock_send_mail.call_count, 2)
        # Проверяем, что вернулось 2 объекта
        self.assertEqual(len(attempts), 2)
        # Проверяем, что они сохранены в БД
        self.assertEqual(Attempt.objects.count(), 2)
        # Проверяем статус попыток
        for attempt in Attempt.objects.all():
            self.assertEqual(attempt.status, Attempt.STATUS_SUCCESS)


class MailingViewTests(TestCase):
    """Тесты доступа к страницам (изоляция данных)."""

    def setUp(self):
        # Добавляем email_confirmed=True, чтобы миксин не перенаправлял нас на логин
        self.user1 = User.objects.create_user(
            email="u1@test.com", password="123", email_confirmed=True
        )
        self.user2 = User.objects.create_user(
            email="u2@test.com", password="123", email_confirmed=True
        )

        self.msg = Message.objects.create(subject="Test", body="Body", owner=self.user1)
        self.mailing1 = Mailing.objects.create(
            start_time=timezone.now(),
            end_time=timezone.now() + timedelta(hours=1),
            message=self.msg,
            owner=self.user1,
        )

    def test_anonymous_redirected(self):
        """Анонимный пользователь перенаправляется на логин."""
        response = self.client.get(reverse("mailings:mailing_list"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/users/login/", response.url)

    def test_user_sees_only_own_mailings(self):
        """Пользователь видит только свои рассылки."""
        # Заходим под вторым пользователем (у него нет рассылок)
        self.client.login(email="u2@test.com", password="123")
        response = self.client.get(reverse("mailings:mailing_list"))

        # Проверяем, что редиректа нет (статус 200)
        self.assertEqual(response.status_code, 200)
        # Убеждаемся, что рассылки первого пользователя (#1) нет в списке
        self.assertNotContains(response, "#1")

        # Заходим под первым пользователем (владельцем рассылки)
        self.client.login(email="u1@test.com", password="123")
        response = self.client.get(reverse("mailings:mailing_list"))
        self.assertEqual(response.status_code, 200)
        # Убеждаемся, что в списке есть рассылка с ID #1
        self.assertContains(response, "#1")
