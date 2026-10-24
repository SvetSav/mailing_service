from django.contrib import admin

from .models import Recipient


@admin.register(Recipient)
class RecipientAdmin(admin.ModelAdmin):
    list_display = ("email", "full_name", "owner")
    search_fields = ("email", "full_name")
