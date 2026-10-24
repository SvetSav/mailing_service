from django.contrib import messages as flash
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import cache_page
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
    View,
)

from clients.models import Recipient
from users.models import User

from .forms import MailingForm, MessageForm
from .mixins import EmailConfirmedRequiredMixin, ManagerRequiredMixin
from .models import Attempt, Mailing, Message
from .services import MailingSendError, send_mailing


# -------------------- Home --------------------
# Кешируем главную страницу на 60 секунд на стороне клиента и сервера
@method_decorator(cache_page(60), name="dispatch")
class HomeView(EmailConfirmedRequiredMixin, View):
    def get(self, request):
        cache_key = f"home_stats_user_{request.user.pk}"
        stats = cache.get(cache_key)

        if stats is None:
            now = timezone.now()
            qs = (
                Mailing.objects.all()
                if request.user.is_manager
                else Mailing.objects.filter(owner=request.user)
            )

            stats = {
                "total": qs.count(),
                # Считаем активные по датам, а не по полю status
                # (так как мы его больше не обновляем при просмотре списка)
                "active": qs.filter(start_time__lte=now, end_time__gte=now).count(),
                "recipients": (
                    Recipient.objects.all().count()
                    if request.user.is_manager
                    else Recipient.objects.filter(owner=request.user).count()
                ),
            }
            cache.set(cache_key, stats, timeout=300)

        return render(request, "mailings/home.html", stats)


# -------------------- Message CRUD --------------------
class MessageListView(LoginRequiredMixin, ListView):
    model = Message
    template_name = "mailings/message_list.html"
    context_object_name = "messages"

    def get_queryset(self):
        return Message.objects.filter(owner=self.request.user)


class MessageCreateView(LoginRequiredMixin, CreateView):
    model = Message
    form_class = MessageForm
    template_name = "mailings/form.html"
    success_url = reverse_lazy("mailings:message_list")
    extra_context = {"title": "Новое сообщение"}

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)


class MessageUpdateView(LoginRequiredMixin, UpdateView):
    model = Message
    form_class = MessageForm
    template_name = "mailings/form.html"
    success_url = reverse_lazy("mailings:message_list")
    extra_context = {"title": "Редактировать сообщение"}

    def get_queryset(self):
        return Message.objects.filter(owner=self.request.user)


class MessageDeleteView(LoginRequiredMixin, DeleteView):
    model = Message
    template_name = "mailings/confirm_delete.html"
    success_url = reverse_lazy("mailings:message_list")

    def get_queryset(self):
        return Message.objects.filter(owner=self.request.user)


# -------------------- Mailing CRUD --------------------
class MailingListView(EmailConfirmedRequiredMixin, ListView):
    model = Mailing
    template_name = "mailings/mailing_list.html"
    context_object_name = "mailings"

    def get_queryset(self):
        qs = (
            Mailing.objects.filter(owner=self.request.user)
            .select_related("message")
            .annotate(rec_count=Count("recipients"))
        )
        return qs


class MailingDetailView(LoginRequiredMixin, DetailView):
    model = Mailing
    template_name = "mailings/mailing_detail.html"
    context_object_name = "mailing"

    def get_queryset(self):
        return Mailing.objects.filter(owner=self.request.user)

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        obj.update_status()
        return obj


class MailingCreateView(LoginRequiredMixin, CreateView):
    model = Mailing
    form_class = MailingForm
    template_name = "mailings/form.html"
    success_url = reverse_lazy("mailings:mailing_list")
    extra_context = {"title": "Новая рассылка"}

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)


class MailingUpdateView(LoginRequiredMixin, UpdateView):
    model = Mailing
    form_class = MailingForm
    template_name = "mailings/form.html"
    success_url = reverse_lazy("mailings:mailing_list")
    extra_context = {"title": "Редактировать рассылку"}

    def get_queryset(self):
        return Mailing.objects.filter(owner=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class MailingDeleteView(LoginRequiredMixin, DeleteView):
    model = Mailing
    template_name = "mailings/confirm_delete.html"
    success_url = reverse_lazy("mailings:mailing_list")

    def get_queryset(self):
        return Mailing.objects.filter(owner=self.request.user)


# -------------------- Отправка --------------------
class MailingSendView(LoginRequiredMixin, View):
    def post(self, request, pk):
        mailing = get_object_or_404(Mailing, pk=pk, owner=request.user)
        mailing.update_status()

        if mailing.status != Mailing.STATUS_STARTED:
            flash.error(
                request,
                f"Сейчас отправка невозможна. Статус: {mailing.status}.",
            )
            return redirect("mailings:mailing_detail", pk=pk)

        try:
            attempts = send_mailing(mailing)
            success = sum(1 for a in attempts if a.status == Attempt.STATUS_SUCCESS)
            flash.success(
                request,
                f"Рассылка выполнена. Успешно: {success}/{len(attempts)}.",
            )
        except MailingSendError as exc:
            flash.error(request, str(exc))

        return redirect("mailings:mailing_detail", pk=pk)


# --------------------  Статистика --------------------
class StatisticsView(EmailConfirmedRequiredMixin, View):
    def get(self, request):
        cache_key = f"stats_user_{request.user.pk}"
        stats = cache.get(cache_key)

        if stats is None:
            mailings = (
                Mailing.objects.all()
                if request.user.is_manager
                else Mailing.objects.filter(owner=request.user)
            )
            attempts = Attempt.objects.filter(mailing__in=mailings)

            stats = {
                "total_mailings": mailings.count(),
                "success_attempts": attempts.filter(
                    status=Attempt.STATUS_SUCCESS
                ).count(),
                "failed_attempts": attempts.filter(
                    status=Attempt.STATUS_FAILED
                ).count(),
                "total_messages": (
                    Message.objects.all().count()
                    if request.user.is_manager
                    else Message.objects.filter(owner=request.user).count()
                ),
            }
            cache.set(cache_key, stats, timeout=300)

        return render(request, "mailings/statistics.html", stats)


# --------------------  Панель менеджера --------------------
class ManagerDashboardView(ManagerRequiredMixin, ListView):
    model = User
    template_name = "mailings/manager_dashboard.html"
    context_object_name = "users"

    def get_queryset(self):
        return User.objects.exclude(pk=self.request.user.pk).order_by("email")


class ToggleUserBlockView(ManagerRequiredMixin, View):
    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        user.is_active = not user.is_active
        user.save()
        return redirect("mailings:manager_dashboard")


class ToggleMailingDisableView(ManagerRequiredMixin, View):
    def post(self, request, pk):
        mailing = get_object_or_404(Mailing, pk=pk)
        mailing.is_disabled = not mailing.is_disabled
        mailing.save()
        return redirect("mailings:mailing_list")
