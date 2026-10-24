from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    # Поля, которые будут отображаться в списке пользователей
    list_display = ("email", "is_manager", "is_active", "email_confirmed", "is_staff")
    list_filter = ("is_manager", "is_active", "email_confirmed", "is_staff")
    search_fields = ("email",)
    ordering = ("email",)

    # Настройка формы редактирования пользователя
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Личная информация", {"fields": ("first_name", "last_name")}),
        (
            "Права доступа",
            {
                "fields": (
                    "is_active",
                    "is_manager",
                    "email_confirmed",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        ("Важные даты", {"fields": ("last_login", "date_joined")}),
    )

    # Настройка формы добавления нового пользователя
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "password1",
                    "password2",
                    "is_manager",
                    "is_active",
                ),
            },
        ),
    )
