from django.urls import path

from . import views

app_name = "mailings"

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    # Messages
    path("messages/", views.MessageListView.as_view(), name="message_list"),
    path("messages/add/", views.MessageCreateView.as_view(), name="message_create"),
    path(
        "messages/<int:pk>/edit/",
        views.MessageUpdateView.as_view(),
        name="message_update",
    ),
    path(
        "messages/<int:pk>/delete/",
        views.MessageDeleteView.as_view(),
        name="message_delete",
    ),
    # Mailings
    path("mailings/", views.MailingListView.as_view(), name="mailing_list"),
    path("mailings/add/", views.MailingCreateView.as_view(), name="mailing_create"),
    path(
        "mailings/<int:pk>/", views.MailingDetailView.as_view(), name="mailing_detail"
    ),
    path(
        "mailings/<int:pk>/edit/",
        views.MailingUpdateView.as_view(),
        name="mailing_update",
    ),
    path(
        "mailings/<int:pk>/delete/",
        views.MailingDeleteView.as_view(),
        name="mailing_delete",
    ),
    path(
        "mailings/<int:pk>/send/", views.MailingSendView.as_view(), name="mailing_send"
    ),
    path("statistics/", views.StatisticsView.as_view(), name="statistics"),
    path("manager/", views.ManagerDashboardView.as_view(), name="manager_dashboard"),
    path(
        "manager/block-user/<int:pk>/",
        views.ToggleUserBlockView.as_view(),
        name="block_user",
    ),
    path(
        "mailings/<int:pk>/toggle-disable/",
        views.ToggleMailingDisableView.as_view(),
        name="toggle_mailing_disable",
    ),
]
