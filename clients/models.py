from django.conf import settings
from django.db import models


class Recipient(models.Model):
    email = models.EmailField("email", unique=True)
    full_name = models.CharField("Ф. И. О.", max_length=200)
    comment = models.TextField("комментарий", blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="recipients",
        verbose_name="владелец",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "получатель"
        verbose_name_plural = "получатели"
        ordering = ["full_name"]

    def __str__(self):
        return f"{self.full_name} <{self.email}>"
