from django.urls import path

from . import views

app_name = "clients"

urlpatterns = [
    path("", views.RecipientListView.as_view(), name="list"),
    path("add/", views.RecipientCreateView.as_view(), name="create"),
    path("<int:pk>/edit/", views.RecipientUpdateView.as_view(), name="update"),
    path("<int:pk>/delete/", views.RecipientDeleteView.as_view(), name="delete"),
]
