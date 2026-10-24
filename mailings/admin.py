from django.contrib import admin

from .models import Attempt, Mailing, Message


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("subject", "owner")


@admin.register(Mailing)
class MailingAdmin(admin.ModelAdmin):
    list_display = ("id", "message", "start_time", "end_time", "status", "owner")
    list_filter = ("status",)


@admin.register(Attempt)
class AttemptAdmin(admin.ModelAdmin):
    list_display = ("id", "mailing", "status", "attempt_time")
