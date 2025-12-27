from django import forms

from .models import Ticket
from .models import TicketStatus


class TicketUpdateForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = [
            "status",
            "priority",
            "assigned_to",
        ]

    def clean(self):
        cleaned = super().clean()
        status = cleaned.get("status")
        assigned_to = cleaned.get("assigned_to")

        # Enforce invariants
        if status == TicketStatus.OPEN and assigned_to:
            self.add_error(
                "assigned_to",
                "Open tickets cannot be assigned.",
            )

        if (
            status
            not in [TicketStatus.OPEN, TicketStatus.COMPLETED, TicketStatus.CANCELED]
            and not assigned_to
        ):
            self.add_error(
                "assigned_to",
                "Assigned user is required unless ticket is open.",
            )

        return cleaned


class TicketClaimForm(forms.Form):
    confirm = forms.BooleanField(required=True)

    def clean(self):
        cleaned = super().clean()
        status = cleaned.get("status")

        if status == TicketStatus.OPEN:
            self.add_error(
                "confirm",
                "Cannot claim tickets that are set to open.",
            )

        return cleaned
