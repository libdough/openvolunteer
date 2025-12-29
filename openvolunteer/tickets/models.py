#!/usr/bin/env python3
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.functional import cached_property

from openvolunteer.orgs.models import Organization

from .actions.enum import TicketActionRunWhen


class TicketStatus(models.TextChoices):
    OPEN = "open", "Open"
    TODO = "todo", "To Do"
    INPROGRESS = "inprogress", "In Progress"
    BLOCKED = "blocked", "Blocked"
    COMPLETED = "completed", "Completed"
    CANCELED = "canceled", "Canceled"


class TicketTemplate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    org = models.ForeignKey(
        Organization,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="ticket_templates",
    )
    # null org => global template

    name = models.CharField(max_length=200)

    description_template = models.TextField(
        help_text="Markdown template rendered into the ticket description",
        default="",
    )
    ticket_name_template = models.CharField(max_length=200)

    action_templates = models.ManyToManyField(
        "tickets.TicketActionTemplate",
        blank=True,
        related_name="ticket_templates",
    )

    default_priority = models.PositiveSmallIntegerField(default=3)

    is_active = models.BooleanField(default=True)
    claimable = models.BooleanField(default=True)

    max_tickets = models.PositiveIntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("org", "name")

    def __str__(self):
        return self.name


class TicketBatch(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    org = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="ticket_batches",
    )

    event = models.ForeignKey(
        "events.Event",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ticket_batches",
    )

    shift = models.ForeignKey(
        "events.Shift",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ticket_batches",
        related_query_name="ticket_batch",
        help_text="Shift this ticket applies to; defaults to event default shift",
    )

    name = models.CharField(max_length=200)
    reason = models.TextField(blank=True)

    claimable = models.BooleanField(default=True)
    default_priority = models.PositiveSmallIntegerField(default=3)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ticket_batches_created",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Ticket(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    org = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="tickets",
    )

    batch = models.ForeignKey(
        TicketBatch,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="tickets",
    )

    event = models.ForeignKey(
        "events.Event",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="tickets",
    )

    shift = models.ForeignKey(
        "events.Shift",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tickets",
        help_text="Shift this ticket applies to; defaults to event default shift",
    )

    person = models.ForeignKey(
        "people.Person",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="tickets",
    )

    name = models.CharField(max_length=200)
    description = models.TextField(
        blank=True,
        help_text="Rendered markdown description for this ticket",
    )

    status = models.CharField(
        max_length=20,
        choices=TicketStatus,
        default=TicketStatus.OPEN,
    )

    class Priority(models.IntegerChoices):
        P0 = 0, "P0 - Emergency (Do Now)"
        P1 = 1, "P1 - Very High"
        P2 = 2, "P2 - High"
        P3 = 3, "P3 - Normal"
        P4 = 4, "P4 - Low"
        P5 = 5, "P5 - Very Low"

    priority = models.PositiveSmallIntegerField(
        choices=Priority.choices,
        default=3,
    )

    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="tickets_assigned",
    )

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="tickets_reported",
    )

    claimable = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Enforce invariants
        if self.status == TicketStatus.OPEN:
            self.assigned_to = None
            self.completed_at = None

        if self.status == TicketStatus.COMPLETED and not self.completed_at:
            self.completed_at = timezone.now()

        if self.status != TicketStatus.COMPLETED:
            self.completed_at = None

        super().save(*args, **kwargs)

    @cached_property
    def manual_actions(self):
        """
        User-visible actions that can be manually triggered.
        """
        return self.actions.filter(
            run_when=TicketActionRunWhen.MANUAL,
        )

    @property
    def is_closed(self):
        return self.status in {TicketStatus.COMPLETED, TicketStatus.CANCELED}


class TicketAuditEvent(models.TextChoices):
    CREATED = "created", "Ticket created"
    UPDATED = "updated", "Ticket updated"
    CLAIMED = "claimed", "Ticket claimed"
    UNCLAIMED = "unclaimed", "Ticket unclaimed"
    STATUS_CHANGED = "status_changed", "Status changed"
    ACTION_RUN = "action_run", "Action executed"
    ACTION_FAILED = "action_failed", "Action failed"
    SYSTEM = "system", "System event"


class TicketAuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    ticket = models.ForeignKey(
        "tickets.Ticket",
        on_delete=models.CASCADE,
        related_name="audit_logs",
    )

    event_type = models.CharField(
        max_length=50,
        choices=TicketAuditEvent,
    )

    message = models.TextField()

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ticket_audit_logs",
        help_text="Null means system",
    )

    metadata = models.JSONField(
        blank=True,
        default=dict,
        help_text="Optional structured context",
    )

    success = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.ticket} - {self.event_type}"
