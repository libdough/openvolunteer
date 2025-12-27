import uuid

from django.db import models

from openvolunteer.tickets.models import TicketStatus


class TicketActionButtonColor(models.TextChoices):
    PRIMARY = "primary", "Primary (blue)"
    DANGER = "danger", "Danger (red)"
    SECONDARY = "secondary", "Secondary (gray)"


class TicketActionType(models.TextChoices):
    UPDATE_SHIFT_STATUS = "update_shift_status", "Update shift assignment status"
    CREATE_SHIFT_ASSIGNMENT = "create_shift_assignment", "Create shift assignment"
    REMOVE_SHIFT_ASSIGNMENT = "remove_shift_assignment", "Remove shift assignment"
    UPDATE_EVENT_STATUS = "update_event_status", "Update event status"


class TicketActionTemplate(models.Model):
    action_type = models.CharField(
        max_length=50,
        choices=TicketActionType,
    )

    label = models.CharField(
        max_length=100,
        help_text="Button label shown to users",
    )

    description = models.TextField(blank=True)

    # JSON schema-like config
    config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Action configuration and defaults",
    )

    # Optional ticket status update
    updates_ticket_status = models.CharField(
        max_length=20,
        blank=True,
        choices=TicketStatus.choices,
    )

    button_color = models.CharField(
        max_length=20,
        choices=TicketActionButtonColor,
        default=TicketActionButtonColor.SECONDARY,
    )

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.label


class TicketAction(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    ticket = models.ForeignKey(
        "tickets.Ticket",
        on_delete=models.CASCADE,
        related_name="actions",
    )

    action_type = models.CharField(
        max_length=50,
        choices=TicketActionType,
    )

    button_color = models.CharField(
        max_length=20,
        choices=TicketActionButtonColor,
        default=TicketActionButtonColor.SECONDARY,
    )

    # Optional ticket status update
    updates_ticket_status = models.CharField(
        max_length=20,
        choices=TicketStatus.choices,
        blank=True,
    )

    label = models.CharField(max_length=100)
    config = models.JSONField(default=dict)

    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    template = models.ForeignKey(
        TicketActionTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ticket_actions",
    )

    def __str__(self):
        return f"{self.label} ({self.ticket})"
