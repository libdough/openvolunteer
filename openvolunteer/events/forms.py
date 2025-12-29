from django import forms

from openvolunteer.orgs.models import Organization
from openvolunteer.people.models import Person

from .models import Event
from .models import Shift
from .models import ShiftAssignment


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = [
            "org",
            "title",
            "template",
            "event_status",
            "starts_at",
            "ends_at",
            "location_name",
            "location_address",
            "description",
            "owned_by",
        ]
        widgets = {
            "starts_at": forms.DateTimeInput(
                attrs={"type": "datetime-local"},
            ),
            "ends_at": forms.DateTimeInput(
                attrs={"type": "datetime-local"},
            ),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        # owned_by should NEVER be required
        self.fields["owned_by"].required = False

        if user:
            self.fields["org"].queryset = Organization.objects.filter(
                memberships__user=user,
                memberships__is_active=True,
            ).distinct()

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


class ShiftAssignmentForm(forms.ModelForm):
    class Meta:
        model = ShiftAssignment
        fields = []


class GenerateTicketsForTemplateForm(forms.Form):
    people = forms.ModelMultipleChoiceField(
        queryset=Person.objects.none(),
        required=False,
        help_text="Leave empty to generate for all eligible people.",
    )

    shift = forms.ModelChoiceField(
        queryset=Shift.objects.none(),
        required=False,
        help_text="Optional: restrict tickets to a specific shift.",
    )

    batch_name = forms.CharField(
        required=False,
        max_length=200,
        help_text="Optional override for the ticket batch name.",
    )

    def __init__(self, *, event, people_queryset, shifts, **kwargs):
        super().__init__(**kwargs)

        self.fields["people"].queryset = people_queryset

        # Only show shift selector if non-default shifts exist
        non_default = shifts.exclude(is_default=True)
        if non_default.exists():
            self.fields["shift"].queryset = non_default
        else:
            self.fields.pop("shift")
