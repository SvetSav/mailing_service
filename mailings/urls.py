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
]
