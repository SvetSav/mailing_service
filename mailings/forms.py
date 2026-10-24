from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import Mailing, Message


class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ["subject", "body"]
        widgets = {
            "subject": forms.TextInput(attrs={"class": "form-control"}),
            "body": forms.Textarea(attrs={"class": "form-control", "rows": 6}),
        }


class MailingForm(forms.ModelForm):
    class Meta:
        model = Mailing
        fields = ["start_time", "end_time", "message", "recipients"]
        widgets = {
            "start_time": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "end_time": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "message": forms.Select(attrs={"class": "form-control"}),
            "recipients": forms.SelectMultiple(
                attrs={"class": "form-control", "size": 8}
            ),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.fields["start_time"].input_formats = ["%Y-%m-%dT%H:%M"]
        self.fields["end_time"].input_formats = ["%Y-%m-%dT%H:%M"]
        if self.user:
            self.fields["message"].queryset = Message.objects.filter(owner=self.user)
            self.fields["recipients"].queryset = self.user.recipients.all()

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("start_time")
        end = cleaned.get("end_time")
        now = timezone.now()
        if start and start < now:
            raise ValidationError("Дата начала не может быть в прошлом.")
        if start and end and start >= end:
            raise ValidationError("Дата начала должна быть раньше даты окончания.")
        return cleaned
