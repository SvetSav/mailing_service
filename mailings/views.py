from django.contrib import messages as flash
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from clients.models import Recipient

from .forms import MailingForm, MessageForm
from .models import Attempt, Mailing, Message
from .services import MailingSendError, send_mailing


# -------------------- Home --------------------
class HomeView(LoginRequiredMixin, View):
    """Главная — статистика с кешированием."""

    def get(self, request):
        cache_key = f"home_stats_user_{request.user.pk}"
        stats = cache.get(cache_key)

        if stats is None:
            now = timezone.now()
            qs = Mailing.objects.filter(owner=request.user)
            stats = {
                "total": qs.count(),
                "active": qs.filter(
                    start_time__lte=now,
                    end_time__gte=now,
                    status=Mailing.STATUS_STARTED,
                ).count(),
                "recipients": Recipient.objects.filter(owner=request.user).count(),
            }
            cache.set(cache_key, stats, timeout=300)

        return __import__("django.shortcuts", fromlist=["render"]).render(
            request, "mailings/home.html", stats
        )


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
class MailingListView(LoginRequiredMixin, ListView):
    model = Mailing
    template_name = "mailings/mailing_list.html"
    context_object_name = "mailings"

    def get_queryset(self):
        qs = Mailing.objects.filter(owner=self.request.user).select_related("message")
        # Обновим статус у каждой рассылки, чтобы список был актуальным
        for m in qs:
            m.update_status()
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
