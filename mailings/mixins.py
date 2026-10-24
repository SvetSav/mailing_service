from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect


class EmailConfirmedRequiredMixin(LoginRequiredMixin):
    """Проверяет, что пользователь авторизован и подтвердил email."""

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not request.user.email_confirmed:
            messages.warning(
                request, "Пожалуйста, подтвердите ваш email. Проверьте почту."
            )
            return redirect("users:login")
        return super().dispatch(request, *args, **kwargs)


class ManagerRequiredMixin(LoginRequiredMixin):
    """Проверяет, что пользователь является менеджером."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_manager and not request.user.is_superuser:
            messages.error(request, "Доступ только для менеджеров.")
            return redirect("mailings:home")
        return super().dispatch(request, *args, **kwargs)
