from django import forms

from .models import Event
from .models import Shift
from .models import ShiftSignup


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = [
            "org",
            "title",
            "event_type",
            "starts_at",
            "ends_at",
            "location_name",
            "location_address",
            "description",
        ]
        widgets = {
            "starts_at": forms.DateTimeInput(
                attrs={"type": "datetime-local"},
            ),
            "ends_at": forms.DateTimeInput(
                attrs={"type": "datetime-local"},
            ),
        }

    def clean(self):
        cleaned = super().clean()
        starts = cleaned.get("starts_at")
        ends = cleaned.get("ends_at")

        if starts and ends and ends <= starts:
            msg = "End time must be after start time."
            raise forms.ValidationError(msg)

        return cleaned


class ShiftForm(forms.ModelForm):
    class Meta:
        model = Shift
        fields = [
            "name",
            "starts_at",
            "ends_at",
            "capacity",
        ]
        widgets = {
            "starts_at": forms.DateTimeInput(
                attrs={"type": "datetime-local"},
            ),
            "ends_at": forms.DateTimeInput(
                attrs={"type": "datetime-local"},
            ),
        }

    def clean(self):
        cleaned = super().clean()
        starts = cleaned.get("starts_at")
        ends = cleaned.get("ends_at")
        capacity = cleaned.get("capacity")

        if starts and ends and ends <= starts:
            msg = "Shift end time must be after start time."
            raise forms.ValidationError(msg)

        if capacity is not None and capacity < 0:
            msg = "Capacity cannot be negative."
            raise forms.ValidationError(msg)

        return cleaned


class ShiftSignupForm(forms.ModelForm):
    class Meta:
        model = ShiftSignup
        fields = ["notes"]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3}),
        }
