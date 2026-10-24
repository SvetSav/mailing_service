from django.conf import settings
from django.db import models
from django.utils import timezone


class Message(models.Model):
    subject = models.CharField("тема письма", max_length=255)
    body = models.TextField("тело письма")
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="messages",
        verbose_name="владелец",
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "сообщение"
        verbose_name_plural = "сообщения"

    def __str__(self):
        return self.subject


class Mailing(models.Model):
    STATUS_CREATED = "Создана"
    STATUS_STARTED = "Запущена"
    STATUS_FINISHED = "Завершена"
    STATUS_CHOICES = [
        (STATUS_CREATED, "Создана"),
        (STATUS_STARTED, "Запущена"),
        (STATUS_FINISHED, "Завершена"),
    ]

    start_time = models.DateTimeField("дата и время начала")
    end_time = models.DateTimeField("дата и время окончания")
    status = models.CharField(
        "статус", max_length=20, choices=STATUS_CHOICES, default=STATUS_CREATED
    )
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name="mailings",
        verbose_name="сообщение",
    )
    recipients = models.ManyToManyField(
        "clients.Recipient",
        related_name="mailings",
        verbose_name="получатели",
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mailings",
        verbose_name="владелец",
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "рассылка"
        verbose_name_plural = "рассылки"
        ordering = ["-start_time"]

    def __str__(self):
        return f"Рассылка #{self.pk} — {self.message.subject}"

    def get_calculated_status(self):
        """Вычисляет статус по текущему времени, не сохраняя в БД."""
        now = timezone.now()
        if now < self.start_time:
            return self.STATUS_CREATED
        if self.start_time <= now <= self.end_time:
            return self.STATUS_STARTED
        return self.STATUS_FINISHED

    def update_status(self, save=True):
        """Пересчитывает и при необходимости сохраняет статус."""
        new_status = self.get_calculated_status()
        if self.status != new_status:
            self.status = new_status
            if save:
                self.save(update_fields=["status"])
        return self.status


class Attempt(models.Model):
    STATUS_SUCCESS = "Успешно"
    STATUS_FAILED = "Не успешно"
    STATUS_CHOICES = [
        (STATUS_SUCCESS, "Успешно"),
        (STATUS_FAILED, "Не успешно"),
    ]

    attempt_time = models.DateTimeField("время попытки", auto_now_add=True)
    status = models.CharField("статус", max_length=20, choices=STATUS_CHOICES)
    server_response = models.TextField("ответ сервера", blank=True)
    mailing = models.ForeignKey(
        Mailing,
        on_delete=models.CASCADE,
        related_name="attempts",
        verbose_name="рассылка",
    )

    class Meta:
        verbose_name = "попытка рассылки"
        verbose_name_plural = "попытки рассылки"
        ordering = ["-attempt_time"]

    def __str__(self):
        return f"{self.mailing_id} — {self.status} — {self.attempt_time:%Y-%m-%d %H:%M}"
