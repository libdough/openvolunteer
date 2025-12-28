import uuid

from django.db import models
from django.db.models.signals import post_save

from openvolunteer.tickets.models import TicketStatus

from .enum import TicketActionButtonColor
from .enum import TicketActionRunWhen
from .enum import TicketActionType


class TicketActionTemplate(models.Model):
    slug = models.SlugField(
        unique=True,
        help_text="Slug to uniquely identify this action template",
    )

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

    run_when = models.CharField(
        max_length=20,
        choices=TicketActionRunWhen.choices,
        default=TicketActionRunWhen.MANUAL,
        help_text=(
            "When this action should be executed. "
            "Manual actions appear as buttons. "
            "Automatic actions run without user interaction."
        ),
    )

    button_color = models.CharField(
        max_length=20,
        choices=TicketActionButtonColor,
        default=TicketActionButtonColor.SECONDARY,
    )

    is_active = models.BooleanField(default=True)

    def __str__(self):
        if self.label:
            return self.label
        return self.slug


# Custom manager to trigger signals on bulk create
class TicketActionManager(models.Manager):
    def bulk_create(self, objs, **kwargs):
        s = super().bulk_create(objs, **kwargs)
        for i in objs:
            # sending post_save signal for individual object
            post_save.send(i.__class__, instance=i, created=True)

        return s


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

    run_when = models.CharField(
        max_length=20,
        choices=TicketActionRunWhen.choices,
        default=TicketActionRunWhen.MANUAL,
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

    # Custom manager to trigger signals on bulk create
    objects = TicketActionManager()

    class Meta:
        indexes = [
            models.Index(
                fields=["ticket", "run_when", "is_completed"],
                name="tic_runwhen_completed_idx",
            ),
        ]

    def __str__(self):
        return f"{self.label} ({self.ticket})"
